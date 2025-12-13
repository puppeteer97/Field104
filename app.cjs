const http = require("http");
const { Client, GatewayIntentBits, Events } = require("discord.js");
const { Worker } = require("worker_threads");
const { fetch } = require("undici");

// ---------------- ENV ----------------
const TOKEN = process.env.DISCORD_TOKEN;
const CHANNEL_ID = process.env.DISCORD_CHANNEL_ID;
const GAME_BOT_ID = process.env.GAME_BOT_ID;
const PORT = process.env.PORT || 3000;

// External keep-alive URL (optional but recommended)
const KEEP_ALIVE_URL = process.env.KEEP_ALIVE_URL;

// ---------------- HTTP SERVER ----------------
const server = http.createServer((req, res) => {
  if (req.url === "/health") {
    res.writeHead(200);
    return res.end("ok");
  }

  res.writeHead(200);
  res.end("OCR bot running");
});

server.listen(PORT, () => {
  console.log(`🌐 HTTP server listening on ${PORT}`);
});

// ---------------- OPTIONAL EXTERNAL PING ----------------
// NOTE: Helps smooth idle cycles but does NOT bypass Render sleep alone
if (KEEP_ALIVE_URL) {
  setInterval(() => {
    fetch(KEEP_ALIVE_URL).catch(() => {});
  }, 5 * 60 * 1000);
}

// ---------------- WORKER QUEUE ----------------
const MAX_WORKERS = 3;
let active = 0;
const queue = [];

function enqueue(buffer) {
  return new Promise((resolve, reject) => {
    queue.push({ buffer, resolve, reject });
    processQueue();
  });
}

function processQueue() {
  if (active >= MAX_WORKERS || queue.length === 0) return;

  const { buffer, resolve, reject } = queue.shift();
  active++;

  runWithRetry(buffer, 0)
    .then(resolve)
    .catch(reject)
    .finally(() => {
      active--;
      processQueue();
    });
}

function runWithRetry(buffer, attempt) {
  return runWorker(buffer).then(out => {
    const g = out?.result?.gValues ?? [];
    const failed = g.length === 3 && g.every(v => v === null);
    if (failed && attempt < 2) return runWithRetry(buffer, attempt + 1);
    return out;
  });
}

function runWorker(buffer) {
  return new Promise((resolve, reject) => {
    const worker = new Worker("./worker.cjs");
    const id = Math.random().toString(36).slice(2);

    worker.postMessage({ id, buffer });

    worker.once("message", msg => {
      if (msg.id === id) {
        worker.terminate();
        resolve(msg);
      }
    });

    worker.once("error", reject);
  });
}

// ---------------- DISCORD ----------------
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent
  ]
});

client.once(Events.ClientReady, () => {
  console.log("🤖 Discord bot online");
});

client.on(Events.MessageCreate, async msg => {
  try {
    if (msg.author.id !== GAME_BOT_ID) return;
    if (msg.channelId !== CHANNEL_ID) return;

    const att = msg.attachments.first();
    if (!att) return;

    const res = await fetch(att.url);
    const buf = Buffer.from(await res.arrayBuffer());

    const out = await enqueue(buf);
    if (out?.result) {
      console.log("G →", out.result.gValues);
    }
  } catch {}
});

client.login(TOKEN);
