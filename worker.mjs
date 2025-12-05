import { parentPort } from "worker_threads";
import { fetch } from "undici";
import sharp from "sharp";
import config from "./config.mjs";

const OCR_API_KEY = config.OCR_API_KEY;

// ---- OCR strip ----
async function ocrStrip(buffer) {
  const full = sharp(buffer);
  const meta = await full.metadata();

  const strip = await full
    .extract({ left: 0, top: 395, width: meta.width, height: 80 })
    .jpeg()
    .toBuffer();

  const base64 = strip.toString("base64");

  const res = await fetch("https://api.ocr.space/parse/image", {
    method: "POST",
    headers: { apikey: OCR_API_KEY, "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      base64Image: `data:image/jpeg;base64,${base64}`,
      language: "eng",
      scale: "true",
      isOverlayRequired: "false"
    })
  });

  return res.json();
}

// ---- Digit normalization ----
function normalizeDigits(str) {
  return str.replace(/I/g, "1").replace(/l/g, "1").replace(/O/g, "0");
}

// ---- All G rules ----
function extractGValues(text) {
  if (!text) return [];
  const lines = text.split(/\r?\n/);
  const out = [];

  for (let raw of lines) {
    if (!raw.trim()) continue;
    const line = raw.trim();

    // Rule 1
    if (/^G[\sA-Za-z]+[0-9]/.test(line)) {
      let d = normalizeDigits(line.replace(/[^0-9]/g, ""));
      if (d) out.push("G" + d);
      continue;
    }

    // Rule 2
    if (/^G\s*\d+/.test(line)) {
      let d = normalizeDigits(line.replace(/[^0-9]/g, ""));
      out.push("G" + d);
      continue;
    }

    // Rule 3
    if (line.startsWith("€")) {
      let d = normalizeDigits(line.replace(/[^0-9]/g, ""));
      if (d) out.push("G" + d);
      continue;
    }

    // Rule 4 — (3xxx
    if (/^\(3\d+/.test(line)) {
      let d = normalizeDigits(line.replace(/[^0-9]/g, "").slice(1));
      if (d) out.push("G" + d);
      continue;
    }

    // Rule 4b — (310
    if (/^\(\d+/.test(line)) {
      let d = normalizeDigits(line.replace(/[^0-9]/g, "").slice(1));
      if (d) out.push("G" + d);
      continue;
    }

    // Rule 5 — 6xxxx / 9xxxx / 1xxxx / 0xxxx
    if (/^[6910]\d+/.test(line)) {
      let d = normalizeDigits(line.replace(/[^0-9]/g, "").slice(1));
      if (d) out.push("G" + d);
      continue;
    }
  }

  return out;
}

// ---- Worker handler ----
parentPort.on("message", async ({ id, buffer }) => {
  try {
    const json = await ocrStrip(buffer);
    const text = json?.ParsedResults?.[0]?.ParsedText || "";
    const gValues = extractGValues(text);

    parentPort.postMessage({
      id,
      err: null,
      result: { text, gValues, confidence: 100 }
    });
  } catch (err) {
    parentPort.postMessage({ id, err: err.message, result: null });
  }
});
