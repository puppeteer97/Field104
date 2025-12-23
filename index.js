const express = require('express');
const fetch = require('node-fetch');

// -----------------------------------
// Configuration from environment
// -----------------------------------
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
const CMD_A_VARIANTS = ['SD', 'sd', 'Sd', 'sD'];

// Bot B Configuration
const BOT_B_ID = '1312830013573169252';
const BOT_B_CHANNEL_ID = '1453016616185892986';
const CMD_B_MIN_DELAY = 630; // seconds
const CMD_B_MAX_DELAY = 750; // seconds
const CMD_B_VARIANTS = ['ns', 'NS', 'Ns', 'nS'];

// Retry settings
const MAX_RETRIES = 5;
const RETRY_DELAY = 5000; // 5 seconds

// Keep-alive settings
const PORT = process.env.PORT || 3000;
const KEEP_ALIVE_INTERVAL = 4 * 60 * 1000; // 4 minutes

// Message tracking
const messageCounts = {
  botA: 0,
  botB: 0,
  errors: 0
};

// Store pending Bot B drops
const pendingDropsB = new Map();

// -----------------------------------
// Utility Functions
// -----------------------------------
function log(msg) {
  const timestamp = new Date().toLocaleString('en-US', { 
    timeZone: 'Asia/Kolkata',
    hour12: false 
  });
  console.log(`[${timestamp}] ${msg}`);
}

function getRandomDelay(min, max) {
  return Math.floor(Math.random() * (max - min + 1) + min);
}

function getRandomVariant(variants) {
  return variants[Math.floor(Math.random() * variants.length)];
}

// -----------------------------------
// Discord HTTP API Functions
// -----------------------------------
async function sendMessage(channelId, content, retries = 0) {
  const url = `https://discord.com/api/v9/channels/${channelId}/messages`;
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': TOKEN,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Origin': 'https://discord.com',
        'Referer': 'https://discord.com/channels/@me',
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'X-Discord-Locale': 'en-US',
        'X-Debug-Options': 'bugReporterEnabled',
        'X-Super-Properties': Buffer.from(JSON.stringify({
          os: 'Windows',
          browser: 'Chrome',
          device: '',
          system_locale: 'en-US',
          browser_user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          browser_version: '120.0.0.0',
          os_version: '10',
          referrer: '',
          referring_domain: '',
          referrer_current: '',
          referring_domain_current: '',
          release_channel: 'stable',
          client_build_number: 259624,
          client_event_source: null
        })).toString('base64')
      },
      body: JSON.stringify({ content }),
      timeout: 10000
    });

    if (response.status === 200 || response.status === 204) {
      return await response.json();
    } else if (response.status === 429) {
      const data = await response.json();
      const retryAfter = (data.retry_after || 60) * 1000;
      log(`⚠️ Rate limited. Retrying after ${retryAfter/1000} seconds...`);
      await new Promise(resolve => setTimeout(resolve, retryAfter));
      return sendMessage(channelId, content, retries);
    } else {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
  } catch (error) {
    if (retries < MAX_RETRIES) {
      log(`⚠️ Send failed (attempt ${retries + 1}/${MAX_RETRIES}): ${error.message}`);
      log(`🔄 Retrying in ${RETRY_DELAY/1000} seconds...`);
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
      return sendMessage(channelId, content, retries + 1);
    } else {
      log(`❌ Failed to send message after ${MAX_RETRIES} attempts`);
      messageCounts.errors++;
      throw error;
    }
  }
}

async function getChannelMessages(channelId, limit = 10) {
  const url = `https://discord.com/api/v9/channels/${channelId}/messages?limit=${limit}`;
  
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': TOKEN,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://discord.com/channels/@me',
        'X-Discord-Locale': 'en-US',
        'X-Super-Properties': Buffer.from(JSON.stringify({
          os: 'Windows',
          browser: 'Chrome',
          device: '',
          system_locale: 'en-US',
          browser_user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          browser_version: '120.0.0.0',
          os_version: '10',
          referrer: '',
          referring_domain: '',
          referrer_current: '',
          referring_domain_current: '',
          release_channel: 'stable',
          client_build_number: 259624,
          client_event_source: null
        })).toString('base64')
      },
      timeout: 10000
    });

    if (response.ok) {
      return await response.json();
    } else {
      throw new Error(`HTTP ${response.status}`);
    }
  } catch (error) {
    log(`⚠️ Failed to fetch messages: ${error.message}`);
    return [];
  }
}

async function clickButton(messageId, channelId, customId, retries = 0) {
  const url = `https://discord.com/api/v9/interactions`;
  
  // Simulate human delay before clicking
  const humanDelay = getRandomDelay(300, 1200);
  await new Promise(resolve => setTimeout(resolve, humanDelay));
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': TOKEN,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Origin': 'https://discord.com',
        'Referer': 'https://discord.com/channels/@me',
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'X-Discord-Locale': 'en-US',
        'X-Super-Properties': Buffer.from(JSON.stringify({
          os: 'Windows',
          browser: 'Chrome',
          device: '',
          system_locale: 'en-US',
          browser_user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          browser_version: '120.0.0.0',
          os_version: '10',
          referrer: '',
          referring_domain: '',
          referrer_current: '',
          referring_domain_current: '',
          release_channel: 'stable',
          client_build_number: 259624,
          client_event_source: null
        })).toString('base64')
      },
      body: JSON.stringify({
        type: 3, // Component interaction
        guild_id: null, // DM channel
        channel_id: channelId,
        message_id: messageId,
        data: {
          component_type: 2, // Button
          custom_id: customId
        }
      }),
      timeout: 10000
    });

    if (response.status === 204 || response.status === 200) {
      return true;
    } else if (response.status === 429) {
      const data = await response.json();
      const retryAfter = (data.retry_after || 60) * 1000;
      log(`⚠️ Rate limited on button click. Retrying after ${retryAfter/1000} seconds...`);
      await new Promise(resolve => setTimeout(resolve, retryAfter));
      return clickButton(messageId, channelId, customId, retries);
    } else {
      throw new Error(`HTTP ${response.status}`);
    }
  } catch (error) {
    if (retries < MAX_RETRIES) {
      log(`⚠️ Button click failed (attempt ${retries + 1}/${MAX_RETRIES}): ${error.message}`);
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
      return clickButton(messageId, channelId, customId, retries + 1);
    } else {
      log(`❌ Failed to click button after ${MAX_RETRIES} attempts`);
      return false;
    }
  }
}

// -----------------------------------
// Bot A Handler (SD Command)
// -----------------------------------
async function botALoop() {
  let cycle = 0;
  
  while (true) {
    try {
      cycle++;
      const command = getRandomVariant(CMD_A_VARIANTS);
      
      log(`[BOT-A] 📤 Sending command: ${command}`);
      const sentMessage = await sendMessage(BOT_A_CHANNEL_ID, command);
      messageCounts.botA++;
      
      log(`[BOT-A] ✅ Sent successfully (cycle ${cycle})`);
      
      // Wait for response and check for drops
      await new Promise(resolve => setTimeout(resolve, 3000));
      await checkBotADrops(sentMessage.id);
      
    } catch (error) {
      log(`[BOT-A] ❌ Error in cycle ${cycle}: ${error.message}`);
    }
    
    const waitTime = getRandomDelay(CMD_A_MIN_DELAY, CMD_A_MAX_DELAY);
    const variance = waitTime * 0.1;
    const finalWait = waitTime + getRandomDelay(-variance, variance);
    
    log(`[BOT-A] ⏰ Next command in ${(finalWait/60).toFixed(1)} minutes\n`);
    await new Promise(resolve => setTimeout(resolve, finalWait * 1000));
  }
}

async function checkBotADrops(ourMessageId) {
  try {
    const messages = await getChannelMessages(BOT_A_CHANNEL_ID, 5);
    
    for (const message of messages) {
      if (message.author.id !== BOT_A_ID) continue;
      if (!message.content.toLowerCase().includes('dropping')) continue;
      if (!message.mentions?.some(m => m.id === message.author.id)) continue;
      
      // Check if it's a reply to our message
      if (message.reference?.message_id !== ourMessageId) continue;
      
      log('[BOT-A] 🎴 Drop detected!');
      
      if (!message.components || message.components.length === 0) {
        log('[BOT-A] ❌ No buttons found');
        continue;
      }
      
      const buttons = message.components[0].components;
      
      // Parse button values
      const parseValue = (label) => {
        if (!label) return 0;
        const str = label.toLowerCase().trim();
        if (str.includes('k')) {
          return Math.floor(parseFloat(str.replace('k', '')) * 1000);
        }
        return parseInt(str) || 0;
      };
      
      const buttonData = buttons.map((button, index) => ({
        index,
        value: parseValue(button.label),
        customId: button.custom_id
      }));
      
      buttonData.forEach(btn => {
        log(`[BOT-A]    Button ${btn.index}: Value = ${btn.value}`);
      });
      
      const maxValue = Math.max(...buttonData.map(btn => btn.value));
      const targetButton = buttonData.find(btn => btn.value === maxValue);
      
      log(`[BOT-A] ✅ Selecting button ${targetButton.index} with value ${targetButton.value}`);
      
      const success = await clickButton(message.id, BOT_A_CHANNEL_ID, targetButton.customId);
      
      if (success) {
        log('[BOT-A] 🎉 Button clicked successfully!');
      }
      
      break;
    }
  } catch (error) {
    log(`[BOT-A] ⚠️ Error checking drops: ${error.message}`);
  }
}

// -----------------------------------
// Bot B Handler (NS Command)
// -----------------------------------
async function botBLoop() {
  let cycle = 0;
  
  while (true) {
    try {
      cycle++;
      const command = getRandomVariant(CMD_B_VARIANTS);
      
      log(`[BOT-B] 📤 Sending command: ${command}`);
      const sentMessage = await sendMessage(BOT_B_CHANNEL_ID, command);
      messageCounts.botB++;
      
      log(`[BOT-B] ✅ Sent successfully (cycle ${cycle})`);
      
      // Wait for response and check for drops
      await new Promise(resolve => setTimeout(resolve, 3000));
      await checkBotBDrops(sentMessage.id);
      
    } catch (error) {
      log(`[BOT-B] ❌ Error in cycle ${cycle}: ${error.message}`);
    }
    
    const waitTime = getRandomDelay(CMD_B_MIN_DELAY, CMD_B_MAX_DELAY);
    const variance = waitTime * 0.1;
    const finalWait = waitTime + getRandomDelay(-variance, variance);
    
    log(`[BOT-B] ⏰ Next command in ${(finalWait/60).toFixed(1)} minutes\n`);
    await new Promise(resolve => setTimeout(resolve, finalWait * 1000));
  }
}

async function checkBotBDrops(ourMessageId) {
  try {
    const messages = await getChannelMessages(BOT_B_CHANNEL_ID, 10);
    
    let buttonMessage = null;
    let statsMessage = null;
    
    // Find the button message (mentions us, has components)
    for (const message of messages) {
      if (message.author.id !== BOT_B_ID) continue;
      
      if (message.components && message.components.length > 0) {
        buttonMessage = message;
      }
      
      // Find stats message (references button message, has WL values)
      if (message.reference && message.content.includes('¦')) {
        if (buttonMessage && message.reference.message_id === buttonMessage.id) {
          statsMessage = message;
          break;
        }
      }
    }
    
    if (!buttonMessage || !statsMessage) {
      return; // No complete drop found
    }
    
    log('[BOT-B] 🎴 Drop detected!');
    log('[BOT-B] 📊 Stats message found!');
    
    // Parse card values from stats message
    const lines = statsMessage.content.split('\n');
    const cardValues = [];
    
    for (let line of lines) {
      const match = line.match(/`\s*(\d+)`\s*<:nwl_s:/);
      if (match) {
        cardValues.push(parseInt(match[1]));
      }
    }
    
    log(`[BOT-B]    Card values: ${cardValues.join(', ')}`);
    
    if (cardValues.length === 0) {
      log('[BOT-B] ❌ No card values found');
      return;
    }
    
    const maxValue = Math.max(...cardValues);
    const highestIndex = cardValues.indexOf(maxValue);
    
    log(`[BOT-B] ✅ Highest value: ${maxValue} at position ${highestIndex + 1}`);
    
    const buttons = buttonMessage.components[0].components;
    const targetButton = buttons[highestIndex];
    
    const success = await clickButton(buttonMessage.id, BOT_B_CHANNEL_ID, targetButton.custom_id);
    
    if (success) {
      log(`[BOT-B] 🎉 Clicked button ${highestIndex + 1} successfully!`);
    }
    
  } catch (error) {
    log(`[BOT-B] ⚠️ Error checking drops: ${error.message}`);
  }
}

// -----------------------------------
// HTTP Keep-Alive Server
// -----------------------------------
const app = express();

app.get('/', (req, res) => {
  const uptime = process.uptime();
  const hours = Math.floor(uptime / 3600);
  const minutes = Math.floor((uptime % 3600) / 60);
  
  res.json({
    status: 'alive',
    uptime: `${hours}h ${minutes}m`,
    messages_sent: messageCounts,
    timestamp: new Date().toISOString()
  });
});

app.get('/ping', (req, res) => {
  res.send('pong');
});

app.get('/stats', (req, res) => {
  res.json(messageCounts);
});

const server = app.listen(PORT, () => {
  log(`🌐 HTTP server running on port ${PORT}`);
  log(`🔗 Keep-alive URL: http://localhost:${PORT}/ping\n`);
});

// Self-ping to keep alive
function selfPing() {
  const url = process.env.RENDER_EXTERNAL_URL || `http://localhost:${PORT}`;
  
  fetch(`${url}/ping`)
    .then(() => log('💓 Keep-alive ping sent'))
    .catch(err => log(`⚠️ Keep-alive ping failed: ${err.message}`));
}

// -----------------------------------
// Graceful Shutdown
// -----------------------------------
process.on('SIGTERM', () => {
  log('📴 SIGTERM signal received: closing server');
  server.close(() => {
    log('✅ Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  log('📴 SIGINT signal received: closing server');
  server.close(() => {
    log('✅ Server closed');
    process.exit(0);
  });
});

// -----------------------------------
// Main Execution
// -----------------------------------
async function main() {
  log('🚀 Starting Discord Bot (HTTP API Method)');
  log('✅ Using stable HTTP-based approach');
  log('👀 Monitoring for drops...\n');
  
  // Random initial delays
  const initialDelayA = getRandomDelay(0, 30);
  const initialDelayB = getRandomDelay(0, 30);
  
  log(`[BOT-A] ⏳ Starting in ${initialDelayA} seconds...`);
  log(`[BOT-B] ⏳ Starting in ${initialDelayB} seconds...\n`);
  
  // Start keep-alive after 30 seconds
  setTimeout(() => {
    log('🔄 Starting keep-alive service...\n');
    selfPing();
    setInterval(selfPing, KEEP_ALIVE_INTERVAL);
  }, 30000);
  
  // Start Bot A loop
  setTimeout(() => {
    botALoop().catch(error => {
      log(`[BOT-A] 💥 Fatal error: ${error.message}`);
    });
  }, initialDelayA * 1000);
  
  // Start Bot B loop
  setTimeout(() => {
    botBLoop().catch(error => {
      log(`[BOT-B] 💥 Fatal error: ${error.message}`);
    });
  }, initialDelayB * 1000);
}

// Start the bot
main().catch(error => {
  log(`💥 Fatal error: ${error.message}`);
  process.exit(1);
});
