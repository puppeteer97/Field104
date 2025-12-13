const { Client, GatewayIntentBits, Events } = require("discord.js");
const { Worker } = require("worker_threads");
const { fetch } = require("undici");

// ---------------- ENV ----------------
const TOKEN = process.env.DISCORD_TOKEN;
const CHANNEL_ID = process.env.DISCORD_CHANNEL_ID;
const GAME_BOT_ID = process.env.GAME_BOT_ID;

// ---------------- WORKER POOL ----------------
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
  console.log("🤖 OCR bot online");
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
  } catch (e) {}
});

client.login(TOKEN);
