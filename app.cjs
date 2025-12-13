const http = require("http");
const { Client, GatewayIntentBits, Events } = require("discord.js");
const { Worker } = require("worker_threads");
const { fetch } = require("undici");

// ---------------- ENV ----------------
const TOKEN = process.env.DISCORD_TOKEN;
const CHANNEL_ID = process.env.DISCORD_CHANNEL_ID;
const GAME_BOT_ID = process.env.GAME_BOT_ID;
const PORT = process.env.PORT || 3000;
const KEEP_ALIVE_URL = process.env.KEEP_ALIVE_URL;

// ---------------- HTTP SERVER ----------------
http.createServer((req, res) => {
  res.writeHead(200);
  res.end("ok");
}).listen(PORT, () => {
  console.log(`[HTTP] listening on ${PORT}`);
});

// ---------------- OPTIONAL EXTERNAL PING ----------------
if (KEEP_ALIVE_URL) {
  setInterval(() => {
    fetch(KEEP_ALIVE_URL).catch(() => {});
  }, 5 * 60 * 1000);
}

// ---------------- PERSISTENT WORKER ----------------
const worker = new Worker("./worker.cjs");

const queue = [];
let busy = false;
let jobId = 0;

worker.on("message", ({ id, result }) => {
  const job = queue.shift();
  busy = false;

  if (job && job.resolve) {
    job.resolve(result);
  }

  processQueue();
});

worker.on("error", err => {
  console.error("[WORKER ERROR]", err);
  busy = false;
});

function enqueue(buffer) {
  return new Promise(resolve => {
    queue.push({ buffer, resolve });
    processQueue();
  });
}

function processQueue() {
  if (busy || queue.length === 0) return;

  busy = true;
  const job = queue[0];

  worker.postMessage({
    id: ++jobId,
    buffer: job.buffer
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

    console.log("[QUEUE] +1 image");
    const result = await enqueue(buf);

    console.log("[OCR RESULT]", result?.gValues);
  } catch (e) {
    console.error("[MSG ERROR]", e);
  }
});

client.login(TOKEN);
