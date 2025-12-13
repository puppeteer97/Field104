const { parentPort } = require("worker_threads");
const sharp = require("sharp");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const os = require("os");

// --------------------------------------------------
// LINUX PATHS (Render)
 // --------------------------------------------------
const TESS_EXE = "/usr/bin/tesseract";
const TESSDATA_DIR = "/app/tessdata";   // repo tessdata copied into Docker

// --------------------------------------------------
// G VALUE PARSER (kept as you had it)
// --------------------------------------------------
function extractG(text) {
  if (!text) return null;

  for (let raw of text.split(/\s+/)) {
    if (!raw) continue;

    let s = raw.toUpperCase().replace(/[^0-9GI]/g, "");
    if (!s) continue;

    // If something like "1G912" → keep from G onward
    const gPos = s.indexOf("G");
    if (gPos > 0) s = s.slice(gPos);

    // 6xxx → Gxxx
    if (/^6\d+/.test(s)) s = "G" + s.slice(1);

    // GL → G1
    if (/^GL/.test(s)) s = "G1" + s.slice(2);

    // GI, GII, GIII...
    if (/^GI+/.test(s)) {
      const m = s.match(/^GI+/)[0];
      const n = "1".repeat(m.length - 1);
      s = "G" + n + s.slice(m.length);
    }

    if (!s.startsWith("G")) continue;

    let digits = s.slice(1).replace(/[^0-9]/g, "");
    if (!digits) continue;

    if (digits.length > 4) digits = digits.slice(-4);

    return "G" + digits;
  }

  return null;
}

// --------------------------------------------------
// PREPROCESS MODES (MULTI-PASS)
// --------------------------------------------------
async function mode1(buf) {
  return sharp(buf)
    .extractChannel("green")
    .normalize()
    .threshold(140)
    .sharpen({ sigma: 1 })
    .png()
    .toBuffer();
}

async function mode2(buf) {
  return sharp(buf)
    .extractChannel("green")
    .normalize()
    .linear(1.6, -10)
    .sharpen({ sigma: 0.3 })
    .png()
    .toBuffer();
}

async function mode3(buf) {
  return sharp(buf)
    .extractChannel("green")
    .normalize()
    .sharpen({ sigma: 0.15 })
    .png()
    .toBuffer();
}

// --------------------------------------------------
// RUN TESSERACT (native Linux)
// --------------------------------------------------
function runNativeTesseract(imgBuffer) {
  return new Promise((resolve) => {
    const tmpDir = os.tmpdir();
    const tempImg = path.join(tmpDir, `ocr_in_${Date.now()}.png`);
    const outBase = path.join(tmpDir, `ocr_out_${Date.now()}`);

    try {
      fs.writeFileSync(tempImg, imgBuffer);
    } catch (e) {
      // if write fails, return empty
      resolve("");
      return;
    }

    const p = spawn(
      TESS_EXE,
      [
        tempImg,
        outBase,
        "--psm", "7",
        "-l", "g",
        "--tessdata-dir", TESSDATA_DIR
      ],
      { stdio: ["ignore", "ignore", "ignore"] }
    );

    p.on("exit", () => {
      try {
        const txt = fs.readFileSync(outBase + ".txt", "utf8");
        // cleanup
        try { fs.unlinkSync(tempImg); } catch (_) {}
        try { fs.unlinkSync(outBase + ".txt"); } catch (_) {}
        resolve(txt);
      } catch {
        try { fs.unlinkSync(tempImg); } catch (_) {}
        resolve("");
      }
    });

    p.on("error", () => {
      try { fs.unlinkSync(tempImg); } catch (_) {}
      resolve("");
    });
  });
}

// --------------------------------------------------
// MULTI-PASS OCR PER CARD
// --------------------------------------------------
async function ocrMultiPass(buf) {
  const variants = [
    await mode1(buf),
    await mode2(buf),
    await mode3(buf)
  ];

  let bestRaw = "";

  for (let i = 0; i < variants.length; i++) {
    const raw = (await runNativeTesseract(variants[i])).trim();
    const g = extractG(raw);

    console.log(`    [Pass ${i + 1}] RAW="${raw}" → ${g}`);

    if (g) return { raw, g };

    if (!bestRaw) bestRaw = raw;
  }

  return { raw: bestRaw, g: null };
}

// --------------------------------------------------
// MAIN OCR PIPELINE
// --------------------------------------------------
async function runOCR(buffer) {
  const strip = await sharp(buffer)
    .extract({ left: 0, top: 427, width: 1008, height: 31 })
    .png()
    .toBuffer();

  const crops = [
    await sharp(strip).extract({ left: 0, top: 0, width: 336, height: 31 }).png().toBuffer(),
    await sharp(strip).extract({ left: 336, top: 0, width: 336, height: 31 }).png().toBuffer(),
    await sharp(strip).extract({ left: 672, top: 0, width: 336, height: 31 }).png().toBuffer()
  ];

  const rawOCR = [];
  const gValues = [];

  for (let i = 0; i < 3; i++) {
    console.log(`\n[C${i + 1}] multi-pass...`);
    const { raw, g } = await ocrMultiPass(crops[i]);

    console.log(`[C${i + 1}] RAW="${raw || "<empty>"}"`);
    console.log(`[C${i + 1}] → ${g}`);

    rawOCR.push(raw);
    gValues.push(g);
  }

  console.log(`→ G: ${JSON.stringify(gValues)}`);
  console.log("------------------------------");

  return { rawOCR, gValues };
}

// --------------------------------------------------
// WORKER LISTENER
// --------------------------------------------------
parentPort.on("message", async ({ id, buffer }) => {
  try {
    const result = await runOCR(buffer);
    parentPort.postMessage({ id, err: null, result });
  } catch (err) {
    parentPort.postMessage({ id, err: err.message, result: null });
  }
});
