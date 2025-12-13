const { parentPort } = require("worker_threads");
const sharp = require("sharp");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const TESS = "/usr/bin/tesseract";
const TESSDATA = process.env.TESSDATA_PREFIX;

// ---------------- LIMITS ----------------
const MAX_PARALLEL = 3;   // 🔥 PROCESS 3 IMAGES AT A TIME
let active = 0;
const queue = [];

// ---------------- PARSER ----------------
function extractAllG(text) {
  if (!text) return [null, null, null];
  const matches = text.toUpperCase().match(/G\d{1,4}/g) || [];
  return [matches[0] || null, matches[1] || null, matches[2] || null];
}

// ---------------- PREPROCESS ----------------
async function preprocessStrip(buf) {
  return sharp(buf)
    .extractChannel("green")
    .resize({ height: 32, kernel: sharp.kernel.nearest })
    .threshold(135)
    .png()
    .toBuffer();
}

// ---------------- TESSERACT ----------------
function ocr(img) {
  return new Promise(resolve => {
    const id = Math.random().toString(36).slice(2);
    const imgPath = path.join(os.tmpdir(), `ocr-${id}.png`);
    const outPath = path.join(os.tmpdir(), `ocr-${id}`);

    fs.writeFileSync(imgPath, img);

    const p = spawn(
      TESS,
      [
        imgPath,
        outPath,
        "-l", "g",
        "--psm", "6",
        "--dpi", "300",
        "--tessdata-dir", TESSDATA,
        "-c", "tessedit_char_whitelist=G0123456789",
        "-c", "load_system_dawg=0",
        "-c", "load_freq_dawg=0",
        "-c", "load_punc_dawg=0",
        "-c", "load_number_dawg=0"
      ],
      { stdio: ["ignore", "ignore", "ignore"] }
    );

    p.on("exit", () => {
      let txt = "";
      try { txt = fs.readFileSync(outPath + ".txt", "utf8").trim(); } catch {}
      fs.rmSync(imgPath, { force: true });
      fs.rmSync(outPath + ".txt", { force: true });
      resolve(txt);
    });

    p.on("error", () => resolve(""));
  });
}

// ---------------- OCR PIPELINE ----------------
async function runOCR(buf) {
  const strip = await sharp(buf)
    .extract({ left: 0, top: 427, width: 1008, height: 31 })
    .png()
    .toBuffer();

  const prep = await preprocessStrip(strip);
  const raw = await ocr(prep);

  return {
    rawOCR: raw,
    gValues: extractAllG(raw)
  };
}

// ---------------- QUEUED EXECUTION ----------------
function enqueueJob(buffer, id) {
  queue.push({ buffer, id });
  processQueue();
}

function processQueue() {
  if (active >= MAX_PARALLEL || queue.length === 0) return;

  const job = queue.shift();
  active++;

  runOCR(job.buffer)
    .then(result => {
      parentPort.postMessage({ id: job.id, result });
    })
    .catch(() => {
      parentPort.postMessage({ id: job.id, result: null });
    })
    .finally(() => {
      active--;
      processQueue();
    });
}

// ---------------- WORKER ENTRY ----------------
parentPort.on("message", ({ id, buffer }) => {
  enqueueJob(buffer, id);
});
