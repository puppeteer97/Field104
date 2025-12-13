const { Client, GatewayIntentBits, Events } = require("discord.js");
const { Worker } = require("worker_threads");
const { fetch } = require("undici");

// ---------------------------------------------------------
// ENV CONFIG (RENDER)
// ---------------------------------------------------------
const TOKEN = process.env.DISCORD_TOKEN;
const CHANNEL_ID = process.env.DISCORD_CHANNEL_ID;
const GAME_BOT_ID = process.env.GAME_BOT_ID;

// ---------------------------------------------------------
// WORKER RUNNER
// ---------------------------------------------------------
function runWorker(buffer) {
  return new Promise((resolve, reject) => {
    const worker = new Worker("./worker.cjs");
    const jobId = Math.random().toString(36).slice(2);

    worker.postMessage({ id: jobId, buffer });

    worker.on("message", msg => {
      if (msg.id === jobId) {
        worker.terminate();
        resolve(msg);
      }
    });

    worker.on("error", reject);
  });
}

// ---------------------------------------------------------
// WORKER POOL (LOW RAM)
// ---------------------------------------------------------
const MAX_WORKERS = 3;
let activeWorkers = 0;
let queue = [];

function queuedWorker(buffer) {
  return new Promise((resolve, reject) => {
    queue.push({ buffer, resolve, reject });
    processQueue();
  });
}

function processQueue() {
  if (activeWorkers >= MAX_WORKERS || queue.length === 0) return;

  const { buffer, resolve, reject } = queue.shift();
  activeWorkers++;

  runWorkerWithRetry(buffer, 0)
    .then(resolve)
    .catch(reject)
    .finally(() => {
      activeWorkers--;
      processQueue();
    });
}

// ---------------------------------------------------------
// RETRY LOGIC
// ---------------------------------------------------------
async function runWorkerWithRetry(buffer, attempt) {
  try {
    const output = await runWorker(buffer);
    const gVals = output?.result?.gValues || [];
    const allNull = gVals.length === 3 && gVals.every(v => v === null);

    if (allNull && attempt < 2) {
      return runWorkerWithRetry(buffer, attempt + 1);
    }
    return output;
  } catch {
    if (attempt < 2) {
      return runWorkerWithRetry(buffer, attempt + 1);
    }
    throw err;
  }
}

// ---------------------------------------------------------
// DISCORD CLIENT
// ---------------------------------------------------------
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent
  ]
});

client.once(Events.ClientReady, () => {
  console.log("🤖 Bot online");
});

// ---------------------------------------------------------
// MESSAGE HANDLER
// ---------------------------------------------------------
client.on(Events.MessageCreate, async (msg) => {
  try {
    if (msg.author.id !== GAME_BOT_ID) return;
    if (msg.channelId !== CHANNEL_ID) return;

    const attachment = msg.attachments.first();
    if (!attachment) return;

    const res = await fetch(attachment.url);
    const buffer = Buffer.from(await res.arrayBuffer());

    const out = await queuedWorker(buffer);
    if (!out?.result) return;

    console.log("G →", out.result.gValues);
  } catch {}
});

// ---------------------------------------------------------
client.login(TOKEN);
