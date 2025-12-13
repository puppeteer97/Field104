const { Client, GatewayIntentBits, Events } = require("discord.js");
const { Worker } = require("worker_threads");
const { fetch } = require("undici");

// ---------------------------------------------------------
// DISCORD CONFIG (ENV VARIABLES)
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
// WORKER POOL
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
  if (activeWorkers >= MAX_WORKERS) return;
  if (queue.length === 0) return;

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
      console.log(`OCR empty → retrying (attempt ${attempt + 2})`);
      return await runWorkerWithRetry(buffer, attempt + 1);
    }

    return output;

  } catch (err) {
    if (attempt < 2) {
      console.log(`Worker/OCR error → retrying (attempt ${attempt + 2})`);
      return await runWorkerWithRetry(buffer, attempt + 1);
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
  console.log(`Logged in as ${client.user.tag}`);
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

    console.log("\n==============================");
    console.log("📸 New image:", attachment.url);
    console.log("==============================");

    const res = await fetch(attachment.url);
    const buffer = Buffer.from(await res.arrayBuffer());

    const workerOutput = await queuedWorker(buffer);

    if (workerOutput.err) {
      console.log("❌ Worker error:", workerOutput.err);
      return;
    }

    const result = workerOutput.result || {};
    const raw = result.rawOCR || [];
    const gValues = result.gValues || [];

    console.log(
      `RAW → [C1] ${raw[0] || "<empty>"}  |  [C2] ${raw[1] || "<empty>"}  |  [C3] ${raw[2] || "<empty>"}`
    );

    console.log("RESULT →", JSON.stringify(gValues));
    console.log("------------------------------");

  } catch (e) {
    console.log("❌ Bot Error:", e.message);
  }
});

// ---------------------------------------------------------
// START BOT
// ---------------------------------------------------------
client.login(TOKEN);
