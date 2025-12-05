console.log("monitor.mjs loaded...");

import { Client, GatewayIntentBits, Events } from "discord.js";
import { Worker } from "worker_threads";
import { fetch } from "undici";

// ---- Environment Variables ----
const TOKEN = process.env.BOT_TOKEN;
const CHANNEL_ID = process.env.CHANNEL_ID;
const GAME_BOT_ID = process.env.GAME_BOT_ID;
const OCR_TIMEOUT_MS = parseInt(process.env.OCR_TIMEOUT_MS || "20000", 10);

// ---- Pushover ----
const PUSHOVER_APP = process.env.PUSHOVER_APP;
const PUSHOVER_USER = process.env.PUSHOVER_USER;

function sendPushover(message) {
  if (!PUSHOVER_APP || !PUSHOVER_USER) return;
  fetch("https://api.pushover.net/1/messages.json", {
    method: "POST",
    body: new URLSearchParams({
      token: PUSHOVER_APP,
      user: PUSHOVER_USER,
      message
    })
  }).catch(() => {});
}

// ---- Worker wrapper ----
function runWorker(buffer) {
  return new Promise((resolve, reject) => {
    const worker = new Worker(new URL("./worker.mjs", import.meta.url), {
      type: "module"
    });

    const id = Math.random().toString(36).slice(2);
    worker.postMessage({ id, buffer });

    const timer = setTimeout(() => {
      worker.terminate();
      reject(new Error("Worker timeout"));
    }, OCR_TIMEOUT_MS);

    worker.on("message", msg => {
      if (msg.id === id) {
        clearTimeout(timer);
        worker.terminate();
        resolve(msg);
      }
    });

    worker.on("error", err => {
      clearTimeout(timer);
      worker.terminate();
      reject(err);
    });
  });
}

// ---- Discord bot ----
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent
  ]
});

client.once(Events.ClientReady, () => {
  console.log("Logged in as:", client.user.tag);
});

client.on(Events.MessageCreate, async msg => {
  try {
    if (msg.author.id !== GAME_BOT_ID) return;
    if (msg.channelId !== CHANNEL_ID) return;

    console.log("\nIncoming message...");

    const attachment = msg.attachments.first();
    if (!attachment) {
      console.log("No image, skipping.");
      return;
    }

    console.log("New image detected:", attachment.url);

    const res = await fetch(attachment.url);
    const buf = Buffer.from(await res.arrayBuffer());

    const { err, result } = await runWorker(buf);
    if (err) {
      console.log("Worker error:", err);
      return;
    }

    console.log("Extracted Text:\n" + result.text);
    console.log("G Values:", result.gValues);
    console.log("Confidence:", result.confidence);
    console.log("--------------------------------------------------");

    // ---- Trigger Pushover for G > 100 ----
    result.gValues.forEach(g => {
      const value = parseInt(g.slice(1), 10);
      if (value > 100) {
        console.log(`G value > 100 detected: ${g}, sending Pushover...`);
        sendPushover(`G value > 100 detected: ${g}`);
      }
    });

  } catch (e) {
    console.log("Bot error:", e.message);
  }
});

// ---- Login ----
client.login(TOKEN);
