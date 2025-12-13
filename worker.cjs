const { parentPort } = require("worker_threads");
const sharp = require("sharp");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const TESS = "/usr/bin/tesseract";
const TESSDATA = process.env.TESSDATA_PREFIX;

// ---------------- PARSER ----------------
function extractG(text) {
  if (!text) return null;
  const m = text.toUpperCase().match(/G\d{1,4}/);
  return m ? m[0] : null;
}

// ---------------- PREPROCESS ----------------
async function preprocess(buf) {
  return sharp(buf)
    .extractChannel("green")
    .resize({ height: 32, kernel: sharp.kernel.nearest })
    .threshold(135)
    .png()
    .toBuffer();
}

// ---------------- TESSERACT (FIXED) ----------------
function ocr(img) {
  return new Promise(resolve => {
    const id = Math.random().toString(36).slice(2);
    const imgPath = path.join(os.tmpdir(), `ocr-${id}.png`);
    const outPath = path.join(os.tmpdir(), `ocr-${id}`);

    fs.writeFileSync(imgPath, img);

    const p = spawn(TESS, [
      imgPath,
      outPath,
      "-l", "g",
      "--psm", "7",
      "--dpi", "300",
      "--tessdata-dir", TESSDATA,
      "-c", "tessedit_char_whitelist=G0123456789",
      "-c", "load_system_dawg=0",
      "-c", "load_freq_dawg=0"
    ], {
      stdio: ["ignore", "ignore", "ignore"] // 🔥 CRITICAL FIX
    });

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

// ---------------- PIPELINE ----------------
async function runOCR(buf) {
  const strip = await sharp(buf)
    .extract({ left: 0, top: 427, width: 1008, height: 31 })
    .png()
    .toBuffer();

  const gValues = [];

  for (let i = 0; i < 3; i++) {
    const crop = await sharp(strip)
      .extract({ left: i * 336, top: 0, width: 336, height: 31 })
      .png()
      .toBuffer();

    const prep = await preprocess(crop);
    const raw = await ocr(prep);
    gValues.push(extractG(raw));
  }

  return { gValues };
}

parentPort.on("message", async ({ id, buffer }) => {
  const result = await runOCR(buffer);
  parentPort.postMessage({ id, result });
});
