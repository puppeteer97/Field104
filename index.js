const { Client } = require('discord.js-selfbot-v13');
const express = require('express');

// Configuration from environment variable
const TOKEN = process.env.AUTH_TOKEN?.trim().replace(/['"]/g, '');

console.log('🔍 Checking AUTH_TOKEN...');
if (!TOKEN) {
  console.error('❌ AUTH_TOKEN environment variable is not set!');
  process.exit(1);
} else {
  console.log('✅ AUTH_TOKEN found');
  console.log(`📏 Token length: ${TOKEN.length} characters`);
  console.log(`🔤 Token preview: ${TOKEN.substring(0, 10)}...${TOKEN.substring(TOKEN.length - 5)}`);
}

// Bot A Configuration
const BOT_A_ID = '853629533855809596';
const BOT_A_CHANNEL_ID = '1452336850415915133';
const CMD_A_MIN_DELAY = 490; // seconds
const CMD_A_MAX_DELAY = 610; // seconds

// Bot B Configuration
const BOT_B_ID = '1312830013573169252';
const BOT_B_CHANNEL_ID = '1453016616185892986';
const CMD_B_MIN_DELAY = 630; // seconds
const CMD_B_MAX_DELAY = 750; // seconds

// Stealth settings
const TYPING_DELAY_MIN = 800; // ms before sending (simulate typing)
const TYPING_DELAY_MAX = 2000; // ms
const BUTTON_CLICK_DELAY_MIN = 300; // ms delay before clicking button
const BUTTON_CLICK_DELAY_MAX = 1200; // ms (simulate human reaction time)

// Keep-alive settings
const PORT = process.env.PORT || 3000;
const KEEP_ALIVE_INTERVAL = 4 * 60 * 1000; // 4 minutes in milliseconds
const MAX_LOGIN_RETRIES = 5;
const RECONNECT_DELAY = 10000; // 10 seconds

let retryCount = 0;
let isReconnecting = false;
let commandLoopsStarted = false;

// Enhanced client configuration
const client = new Client({
  checkUpdate: false,
  readyStatus: false,
  captchaService: undefined,
  captchaKey: undefined,
  DMSync: false,
  patchVoice: false,
  ws: {
    properties: {
      browser: 'Discord Client',
      os: 'Windows'
    },
    large_threshold: 50
  },
  http: {
    version: 9,
    api: 'https://discord.com/api'
  }
});

// Store pending Bot B drops
let pendingDropsB = new Map();

// Random delay helper
function getRandomDelay(min, max) {
  return Math.floor(Math.random() * (max - min + 1) + min);
}

// Random command A variant
function getRandomCmdA() {
  const variants = ['SD', 'sd', 'Sd', 'sD'];
  return variants[Math.floor(Math.random() * variants.length)];
}

// Random command B variant
function getRandomCmdB() {
  const variants = ['ns', 'NS', 'Ns', 'nS'];
  return variants[Math.floor(Math.random() * variants.length)];
}

// Simulate human typing
async function simulateTyping(channel) {
  const typingTime = getRandomDelay(TYPING_DELAY_MIN, TYPING_DELAY_MAX);
  await channel.sendTyping();
  await new Promise(resolve => setTimeout(resolve, typingTime));
}

// Send command to Bot A
async function sendCommandA() {
  try {
    const channel = await client.channels.fetch(BOT_A_CHANNEL_ID);
    await simulateTyping(channel);
    
    const command = getRandomCmdA();
    await channel.send(command);
    console.log(`[BOT-A] 📤 Sent: ${command}`);
  } catch (error) {
    console.error('[BOT-A] ❌ Error sending command:', error.message);
  }
}

// Send command to Bot B
async function sendCommandB() {
  try {
    const channel = await client.channels.fetch(BOT_B_CHANNEL_ID);
    await simulateTyping(channel);
    
    const command = getRandomCmdB();
    await channel.send(command);
    console.log(`[BOT-B] 📤 Sent: ${command}`);
  } catch (error) {
    console.error('[BOT-B] ❌ Error sending command:', error.message);
  }
}

// Schedule next command for Bot A
function scheduleNextA() {
  const baseDelay = getRandomDelay(CMD_A_MIN_DELAY, CMD_A_MAX_DELAY);
  const variance = baseDelay * 0.1;
  const finalDelay = baseDelay + getRandomDelay(-variance, variance);
  
  const minutes = (finalDelay / 60).toFixed(1);
  console.log(`[BOT-A] ⏰ Next command in ${minutes} minutes\n`);
  
  setTimeout(async () => {
    await sendCommandA();
    scheduleNextA();
  }, finalDelay * 1000);
}

// Schedule next command for Bot B
function scheduleNextB() {
  const baseDelay = getRandomDelay(CMD_B_MIN_DELAY, CMD_B_MAX_DELAY);
  const variance = baseDelay * 0.1;
  const finalDelay = baseDelay + getRandomDelay(-variance, variance);
  
  const minutes = (finalDelay / 60).toFixed(1);
  console.log(`[BOT-B] ⏰ Next command in ${minutes} minutes\n`);
  
  setTimeout(async () => {
    await sendCommandB();
    scheduleNextB();
  }, finalDelay * 1000);
}

// Start command loops (only once)
function startCommandLoops() {
  if (commandLoopsStarted) {
    console.log('⚠️ Command loops already started, skipping...');
    return;
  }
  
  commandLoopsStarted = true;
  
  // Random initial delays before first commands
  const initialDelayA = getRandomDelay(0, 30000);
  const initialDelayB = getRandomDelay(0, 30000);
  
  console.log(`[BOT-A] ⏳ Waiting ${(initialDelayA/1000).toFixed(0)}s before first command...`);
  console.log(`[BOT-B] ⏳ Waiting ${(initialDelayB/1000).toFixed(0)}s before first command...\n`);
  
  // Start Bot A loop
  setTimeout(async () => {
    await sendCommandA();
    scheduleNextA();
  }, initialDelayA);
  
  // Start Bot B loop
  setTimeout(async () => {
    await sendCommandB();
    scheduleNextB();
  }, initialDelayB);
}

// WebSocket debugging
client.ws.on('open', () => {
  console.log('🌐 WebSocket opened');
});

client.ws.on('close', (code, reason) => {
  console.log(`🔌 WebSocket closed with code: ${code}, reason: ${reason}`);
  
  // Don't reconnect if we're already reconnecting or if it was a clean close
  if (!isReconnecting && code !== 1000) {
    handleDisconnection();
  }
});

client.on('debug', (info) => {
  if (info.includes('Preparing') || info.includes('Identifying') || info.includes('Heartbeat')) {
    console.log('🔍 Debug:', info);
  }
});

// Handle disconnections
function handleDisconnection() {
  if (isReconnecting) return;
  
  isReconnecting = true;
  console.log('⚠️ Connection lost! Attempting to reconnect...');
  
  setTimeout(() => {
    console.log('🔄 Reconnecting...');
    client.destroy();
    loginWithRetry();
  }, RECONNECT_DELAY);
}

client.on('ready', async () => {
  console.log('🎊 READY EVENT FIRED!');
  console.log(`✅ Logged in as ${client.user.tag}`);
  console.log(`👤 User ID: ${client.user.id}`);
  console.log('👀 Monitoring bot responses...');
  console.log('🤖 Auto-sending commands...\n');
  
  isReconnecting = false;
  retryCount = 0; // Reset retry count on successful connection
  
  startCommandLoops();
});

client.on('messageCreate', async (message) => {
  // ===== BOT A HANDLER =====
  if (message.author.id === BOT_A_ID) {
    if (!message.mentions.has(client.user.id)) return;
    if (!message.content.toLowerCase().includes('dropping')) return;
    
    // SAFETY CHECK: Verify this is a direct reply to our message
    if (message.reference) {
      try {
        const repliedTo = await message.channel.messages.fetch(message.reference.messageId);
        if (repliedTo.author.id !== client.user.id) {
          console.log('[BOT-A] ⚠️ Response not replying to our message, skipping...');
          return;
        }
      } catch (error) {
        console.log('[BOT-A] ⚠️ Could not verify message reference, skipping...');
        return;
      }
    }
    
    console.log('[BOT-A] 🎴 Drop detected!');
    
    // Human-like reaction time
    const reactionDelay = getRandomDelay(BUTTON_CLICK_DELAY_MIN, BUTTON_CLICK_DELAY_MAX);
    await new Promise(resolve => setTimeout(resolve, reactionDelay));
    
    try {
      const buttons = message.components?.[0]?.components || [];
      
      if (buttons.length === 0) {
        console.log('[BOT-A] ❌ No buttons found');
        return;
      }
      
      // Parse button values (handle k notation)
      const parseValue = (label) => {
        if (!label) return 0;
        const str = label.toLowerCase().trim();
        
        if (str.includes('k')) {
          const num = parseFloat(str.replace('k', ''));
          return Math.floor(num * 1000);
        }
        
        return parseInt(str) || 0;
      };
      
      const buttonData = buttons.map((button, index) => ({
        index,
        value: parseValue(button.label),
        customId: button.customId
      }));
      
      buttonData.forEach(btn => {
        console.log(`[BOT-A]    Button ${btn.index}: Value = ${btn.value}`);
      });
      
      const maxValue = Math.max(...buttonData.map(btn => btn.value));
      const targetButton = buttonData.find(btn => btn.value === maxValue);
      
      console.log(`[BOT-A] ✅ Selecting button ${targetButton.index} with value ${targetButton.value}`);
      
      await message.clickButton(targetButton.customId);
      console.log('[BOT-A] 🎉 Button clicked successfully!\n');
      
    } catch (error) {
      console.error('[BOT-A] ❌ Error clicking button:', error.message);
    }
  }
  
  // ===== BOT B HANDLER =====
  if (message.author.id === BOT_B_ID) {
    // First message: has buttons and mentions us
    if (message.mentions.has(client.user.id) && message.components && message.components.length > 0) {
      console.log('[BOT-B] 🎴 Drop detected (first message with buttons)!');
      
      pendingDropsB.set(message.id, {
        message: message,
        timestamp: Date.now()
      });
      
      // Clean up old pending drops
      for (let [id, data] of pendingDropsB.entries()) {
        if (Date.now() - data.timestamp > 30000) {
          pendingDropsB.delete(id);
        }
      }
      return;
    }
    
    // Second message: has stats with WL values
    if (message.reference && message.content.includes('¦')) {
      console.log('[BOT-B] 📊 Stats message detected!');
      
      const firstMessageId = message.reference.messageId;
      let dropData = pendingDropsB.get(firstMessageId);
      
      // Try to fetch if not in pending
      if (!dropData) {
        try {
          const firstMessage = await message.channel.messages.fetch(firstMessageId);
          if (firstMessage.author.id === BOT_B_ID && firstMessage.components.length > 0) {
            console.log('[BOT-B]    Found button message from reference');
            dropData = { message: firstMessage, timestamp: Date.now() };
          }
        } catch (error) {
          console.log('[BOT-B] ⚠️ Could not find corresponding button message');
          return;
        }
      }
      
      if (!dropData) {
        console.log('[BOT-B] ⚠️ Could not find corresponding button message');
        return;
      }
      
      // Parse card values
      const lines = message.content.split('\n');
      const cardValues = [];
      
      for (let line of lines) {
        const match = line.match(/`\s*(\d+)`\s*<:nwl_s:/);
        if (match) {
          cardValues.push(parseInt(match[1]));
        }
      }
      
      console.log(`[BOT-B]    Card values: ${cardValues.join(', ')}`);
      
      if (cardValues.length === 0) {
        console.log('[BOT-B] ❌ No card values found');
        return;
      }
      
      const maxValue = Math.max(...cardValues);
      const highestIndex = cardValues.indexOf(maxValue);
      
      console.log(`[BOT-B] ✅ Highest value: ${maxValue} at position ${highestIndex + 1}`);
      
      // Human-like reaction time
      const reactionDelay = getRandomDelay(BUTTON_CLICK_DELAY_MIN, BUTTON_CLICK_DELAY_MAX);
      await new Promise(resolve => setTimeout(resolve, reactionDelay));
      
      try {
        const buttons = dropData.message.components[0].components;
        const targetButton = buttons[highestIndex];
        
        await dropData.message.clickButton(targetButton.customId);
        console.log(`[BOT-B] 🎉 Clicked button ${highestIndex + 1} successfully!\n`);
        
        pendingDropsB.delete(firstMessageId);
        
      } catch (error) {
        console.error('[BOT-B] ❌ Error clicking button:', error.message);
      }
    }
  }
});

// Enhanced error handling
client.on('error', (error) => {
  console.error('⚠️ Client error:', error.message);
  
  // Don't reconnect on certain errors
  if (error.message.includes('ECONNRESET') || error.message.includes('ETIMEDOUT')) {
    console.log('Network error detected, will attempt to reconnect...');
    handleDisconnection();
  }
});

client.on('shardError', error => {
  console.error('⚠️ Shard error:', error);
});

process.on('unhandledRejection', (error) => {
  console.error('⚠️ Unhandled rejection:', error);
  
  // Don't crash the process on unhandled rejections
  if (error.message && error.message.includes('WebSocket')) {
    console.log('WebSocket error in promise, attempting recovery...');
  }
});

process.on('uncaughtException', (error) => {
  console.error('⚠️ Uncaught exception:', error);
  
  // Only exit on critical errors
  if (error.message && !error.message.includes('WebSocket')) {
    console.error('Critical error, exiting...');
    process.exit(1);
  }
});

// ===== HTTP SERVER FOR KEEP-ALIVE =====
const app = express();

// Health check endpoint
app.get('/', (req, res) => {
  const uptime = process.uptime();
  const hours = Math.floor(uptime / 3600);
  const minutes = Math.floor((uptime % 3600) / 60);
  
  res.json({
    status: 'alive',
    uptime: `${hours}h ${minutes}m`,
    user: client.user ? client.user.tag : 'Not logged in',
    connected: client.ws.status === 0,
    timestamp: new Date().toISOString()
  });
});

// Ping endpoint for keep-alive
app.get('/ping', (req, res) => {
  res.send('pong');
});

// Status endpoint
app.get('/status', (req, res) => {
  res.json({
    connected: client.ws.status === 0,
    user: client.user ? client.user.tag : null,
    retries: retryCount,
    reconnecting: isReconnecting
  });
});

// Start Express server
const server = app.listen(PORT, () => {
  console.log(`🌐 HTTP server running on port ${PORT}`);
  console.log(`🔗 Keep-alive URL: http://localhost:${PORT}/ping\n`);
});

// Self-ping mechanism to keep service awake
function selfPing() {
  const url = process.env.RENDER_EXTERNAL_URL || `http://localhost:${PORT}`;
  
  fetch(`${url}/ping`)
    .then(() => console.log('💓 Keep-alive ping sent'))
    .catch(err => console.log('⚠️ Keep-alive ping failed:', err.message));
}

// Start self-pinging after client is ready
client.once('ready', () => {
  console.log('🔄 Starting keep-alive service...\n');
  
  // Ping immediately
  setTimeout(selfPing, 30000); // Wait 30s before first ping
  
  // Then ping every 4 minutes
  setInterval(selfPing, KEEP_ALIVE_INTERVAL);
});

// Login with retry logic
async function loginWithRetry() {
  if (retryCount >= MAX_LOGIN_RETRIES) {
    console.error('❌ Max login retries reached. Exiting.');
    process.exit(1);
  }
  
  console.log(`🔐 Login attempt ${retryCount + 1}/${MAX_LOGIN_RETRIES}...`);
  
  const loginTimeout = setTimeout(() => {
    console.error('⏰ Login timeout - no response after 60 seconds');
    retryCount++;
    
    if (retryCount < MAX_LOGIN_RETRIES) {
      console.log('🔄 Retrying login...\n');
      client.destroy();
      setTimeout(() => loginWithRetry(), 5000);
    } else {
      console.error('❌ Max retries reached. Exiting.');
      process.exit(1);
    }
  }, 60000); // 60 second timeout

  try {
    await client.login(TOKEN);
    console.log('✅ Login promise resolved!');
    clearTimeout(loginTimeout);
  } catch (error) {
    clearTimeout(loginTimeout);
    console.error('❌ Login failed!');
    console.error('Error:', error.message);
    console.error('Error code:', error.code);
    
    retryCount++;
    
    if (retryCount < MAX_LOGIN_RETRIES) {
      console.log(`🔄 Retrying in 5 seconds... (attempt ${retryCount + 1}/${MAX_LOGIN_RETRIES})\n`);
      await new Promise(resolve => setTimeout(resolve, 5000));
      return loginWithRetry();
    } else {
      console.error('❌ Max retries reached. Exiting.');
      process.exit(1);
    }
  }
}

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('📴 SIGTERM signal received: closing HTTP server and Discord client');
  server.close(() => {
    console.log('HTTP server closed');
  });
  client.destroy();
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('📴 SIGINT signal received: closing HTTP server and Discord client');
  server.close(() => {
    console.log('HTTP server closed');
  });
  client.destroy();
  process.exit(0);
});

// Start the bot
loginWithRetry();
