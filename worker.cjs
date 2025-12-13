const { parentPort } = require("worker_threads");
const sharp = require("sharp");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

// --------------------------------------------------
// TESSERACT (RENDER / DOCKER)
// --------------------------------------------------
const TESS_EXE = process.env.TESS_EXE || "/usr/bin/tesseract";
const TESSDATA_DIR = process.env.TESSDATA_DIR || path.join(__dirname, "tessdata");

// --------------------------------------------------
// G PARSER (UNCHANGED LOGIC)
// --------------------------------------------------
function extractG(text) {
  if (!text) return null;

  for (let raw of text.split(/\s+/)) {
    let s = raw.toUpperCase().replace(/[^0-9GI]/g, "");
    if (!s) continue;

    const gPos = s.indexOf("G");
    if (gPos > 0) s = s.slice(gPos);
    if (/^6\d+/.test(s)) s = "G" + s.slice(1);
    if (/^GL/.test(s)) s = "G1" + s.slice(2);
    if (/^GI+/.test(s)) s = "G" + "1".repeat(s.length - 1);

    if (!s.startsWith("G")) continue;

    let digits = s.slice(1).replace(/\D/g, "");
    if (!digits) continue;

    return "G" + digits.slice(-4);
  }
  return null;
}

// --------------------------------------------------
// PREPROCESS (ACCURACY TUNED)
// --------------------------------------------------
async function preprocess(buf) {
  return sharp(buf)
    .extractChannel("green")
    .resize({ height: 40 })
    .normalize()
    .threshold(135)
    .sharpen()
    .png()
    .toBuffer();
}

// --------------------------------------------------
// TESSERACT RUN
// --------------------------------------------------
function runTesseract(img) {
  return new Promise((resolve) => {
    const imgPath = path.join(__dirname, "ocr.png");
    const outPath = path.join(__dirname, "ocr");

    fs.writeFileSync(imgPath, img);

    const p = spawn(TESS_EXE, [
      imgPath,
      outPath,
      "--dpi", "300",
      "--psm", "7",
      "-l", "g",
      "--tessdata-dir", TESSDATA_DIR,
      "-c", "tessedit_char_whitelist=G0123456789"
    ]);

    p.on("exit", () => {
      try {
        resolve(fs.readFileSync(outPath + ".txt", "utf8").trim());
      } catch {
        resolve("");
      }
    });

    p.on("error", () => resolve(""));
  });
}

// --------------------------------------------------
// OCR PIPELINE
// --------------------------------------------------
async function runOCR(buffer) {
  const strip = await sharp(buffer)
    .extract({ left: 0, top: 427, width: 1008, height: 31 })
    .png()
    .toBuffer();

  const results = [];

  for (let i = 0; i < 3; i++) {
    const crop = await sharp(strip)
      .extract({ left: i * 336, top: 0, width: 336, height: 31 })
      .png()
      .toBuffer();

    const prep = await preprocess(crop);
    const raw = await runTesseract(prep);
    results.push({ raw, g: extractG(raw) });
  }

  return {
    rawOCR: results.map(r => r.raw),
    gValues: results.map(r => r.g)
  };
}

// --------------------------------------------------
parentPort.on("message", async ({ id, buffer }) => {
  try {
    const result = await runOCR(buffer);
    parentPort.postMessage({ id, err: null, result });
  } catch (e) {
    parentPort.postMessage({ id, err: e.message, result: null });
  }
});
