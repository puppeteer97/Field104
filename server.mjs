import express from "express";
import { fetch } from "undici";
import "./monitor.mjs";

const app = express();
app.get("/", (req, res) => res.send("G OCR Bot active."));

// ---- Keepalive ----
const KEEPALIVE_URL = process.env.KEEPALIVE_URL;
if (KEEPALIVE_URL) {
  console.log("Keepalive enabled →", KEEPALIVE_URL);
  setInterval(() => {
    fetch(KEEPALIVE_URL).catch(() => {});
    console.log(new Date().toISOString(), "Ping", KEEPALIVE_URL);
  }, 4 * 60 * 1000);
} else {
  console.log("Keepalive disabled (no KEEPALIVE_URL)");
}

// ---- Server port ----
const PORT = process.env.PORT ? parseInt(process.env.PORT) : 3000;
app.listen(PORT, () => {
  console.log("Server listening on port", PORT);
});
