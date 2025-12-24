import requests
import time
import random
import os
import threading
from datetime import datetime
from flask import Flask, jsonify

# -----------------------------------
# Configuration
# -----------------------------------
TOKEN = os.environ.get("AUTH_TOKEN", "").strip()

# Bot IDs
BOT_A_ID = '853629533855809596'
GUILD_ID = '1452333704062959677'

# Channels
CHANNEL_SD = '1452336850415915133'
CHANNEL_NS = '1453016616185892986'

# Messages
SD_MESSAGES = ['SD', 'sd', 'Sd', 'sD']
NS_MESSAGES = ['ns', 'NS', 'Ns', 'nS']

# Delays
SD_MIN = 500
SD_MAX = 620
NS_MIN = 640
NS_MAX = 760

MAX_RETRIES = 3
RETRY_DELAY = 10

# -----------------------------------
# Setup
# -----------------------------------
app = Flask(__name__)
message_counts = {'sd': 0, 'ns': 0, 'clicks': 0, 'click_fails': 0}

def get_session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    return s

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

# -----------------------------------
# Send Message
# -----------------------------------
def send_message(channel_id, msg):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    session = get_session()
    headers = {
        "Authorization": TOKEN,
        "Content-Type": "application/json"
    }
    data = {"content": msg}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.post(url, headers=headers, json=data, timeout=15)
            
            if r.status_code in [200, 201, 204]:
                log(f"✅ Sent '{msg}' to channel {channel_id}")
                try:
                    return r.json()
                except:
                    return {"id": "unknown"}
            elif r.status_code == 429:
                retry_after = 300
                try:
                    retry_after = int(r.headers.get('Retry-After', 300))
                except:
                    pass
                log(f"⚠ Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
                return None
            else:
                log(f"⚠ Status {r.status_code}: {r.text[:200]}")
                
        except Exception as e:
            log(f"❌ Error: {str(e)[:100]}")

        if attempt < MAX_RETRIES:
            wait = RETRY_DELAY * (2 ** (attempt - 1))
            time.sleep(wait)

    return None

# -----------------------------------
# Get Messages
# -----------------------------------
def get_messages(channel_id):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=5"
    session = get_session()
    headers = {"Authorization": TOKEN}
    
    try:
        time.sleep(random.uniform(2.0, 3.5))
        r = session.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
        else:
            log(f"⚠ Get messages status: {r.status_code}")
    except Exception as e:
        log(f"⚠ Get messages error: {e}")
    return []

# -----------------------------------
# Click Button - IMPROVED
# -----------------------------------
def click_button(message_id, channel_id, custom_id, button_index, value):
    url = "https://discord.com/api/v9/interactions"
    session = get_session()
    
    headers = {
        "Authorization": TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    payload = {
        "type": 3,
        "guild_id": GUILD_ID,
        "channel_id": channel_id,
        "message_id": message_id,
        "data": {
            "component_type": 2,
            "custom_id": custom_id
        }
    }
    
    log(f"🔘 Attempting to click button {button_index} (value: {value})")
    log(f"   Message ID: {message_id}")
    log(f"   Custom ID: {custom_id}")
    log(f"   Channel: {channel_id}")
    
    try:
        # Human-like delay
        delay = random.uniform(1.5, 3.5)
        log(f"   Waiting {delay:.1f}s before clicking...")
        time.sleep(delay)
        
        r = session.post(url, headers=headers, json=payload, timeout=15)
        
        log(f"   Click response status: {r.status_code}")
        
        if r.status_code in [200, 204]:
            log(f"✅ Successfully clicked button {button_index} (value: {value})!")
            return True
        elif r.status_code == 404:
            log(f"❌ Button not found (already claimed or expired)")
        elif r.status_code == 400:
            log(f"❌ Invalid interaction: {r.text[:200]}")
        else:
            log(f"❌ Click failed: {r.status_code} - {r.text[:200]}")
            
    except Exception as e:
        log(f"❌ Click exception: {e}")
    
    return False

# -----------------------------------
# Check SD Drop - IMPROVED
# -----------------------------------
def check_sd_drop(our_message_id=None):
    try:
        log("🔍 Checking for SD drops...")
        messages = get_messages(CHANNEL_SD)
        
        log(f"📥 Found {len(messages)} messages in channel")
        
        for i, msg in enumerate(messages):
            author_id = msg.get('author', {}).get('id')
            author_name = msg.get('author', {}).get('username', 'Unknown')
            content = msg.get('content', '')
            msg_id = msg.get('id')
            
            log(f"   Message {i}: From {author_name} ({author_id})")
            log(f"      Content: {content[:50]}")
            log(f"      Message ID: {msg_id}")
            
            # Check if it's from the game bot
            if author_id != BOT_A_ID:
                log(f"      ❌ Not from game bot")
                continue
            
            # Check if it mentions dropping
            if 'dropping' not in content.lower():
                log(f"      ❌ Doesn't mention 'dropping'")
                continue
            
            # Check if it has components (buttons)
            components = msg.get('components', [])
            if not components:
                log(f"      ❌ No components found")
                continue
            
            log(f"      ✅ VALID DROP MESSAGE FOUND!")
            
            buttons = components[0].get('components', [])
            if not buttons:
                log(f"      ❌ No buttons in component")
                continue
            
            log(f"      📋 Found {len(buttons)} buttons")
            
            # Parse all button values
            button_data = []
            for idx, btn in enumerate(buttons):
                label = btn.get('label', '')
                custom_id = btn.get('custom_id', '')
                
                # Parse value from label
                val = 0
                try:
                    label_str = str(label).lower().strip()
                    if 'k' in label_str:
                        val = int(float(label_str.replace('k', '')) * 1000)
                    elif label_str:
                        val = int(label_str)
                except:
                    val = 0
                
                button_data.append({
                    'index': idx,
                    'label': label,
                    'value': val,
                    'custom_id': custom_id
                })
                
                log(f"         Button {idx}: Label='{label}' Value={val} CustomID={custom_id[:20]}...")
            
            # Find button with highest value
            best_button = max(button_data, key=lambda x: x['value'])
            
            log(f"      🎯 Highest value button: {best_button['index']} with value {best_button['value']}")
            
            # Click the button
            success = click_button(
                msg_id,
                CHANNEL_SD,
                best_button['custom_id'],
                best_button['index'],
                best_button['value']
            )
            
            if success:
                message_counts['clicks'] += 1
            else:
                message_counts['click_fails'] += 1
            
            # Only process the first valid drop
            break
            
    except Exception as e:
        log(f"⚠️ Check SD drop error: {e}")
        import traceback
        log(traceback.format_exc())

# -----------------------------------
# SD Loop
# -----------------------------------
def sd_loop():
    cycle = 0
    initial_delay = random.randint(5, 30)
    log(f"🔵 SD bot starting in {initial_delay}s...")
    time.sleep(initial_delay)
    
    while True:
        cycle += 1
        msg = random.choice(SD_MESSAGES)
        
        log(f"🔵 SD Cycle {cycle}: Sending '{msg}'")
        sent = send_message(CHANNEL_SD, msg)
        
        if sent:
            message_counts['sd'] += 1
            
            # Always check for drops after sending
            try:
                check_sd_drop(sent.get('id'))
            except Exception as e:
                log(f"⚠️ Drop check failed: {e}")
        else:
            log(f"❌ Failed to send SD message")
        
        base_wait = random.randint(SD_MIN, SD_MAX)
        variance = int(base_wait * 0.1)
        wait = base_wait + random.randint(-variance, variance)
        
        log(f"🔵 SD cycle {cycle} complete. Next in {wait}s ({wait//60}m {wait%60}s)\n")
        time.sleep(wait)

# -----------------------------------
# NS Loop
# -----------------------------------
def ns_loop():
    cycle = 0
    initial_delay = random.randint(10, 40)
    log(f"🟣 NS bot starting in {initial_delay}s...")
    time.sleep(initial_delay)
    
    while True:
        cycle += 1
        msg = random.choice(NS_MESSAGES)
        
        log(f"🟣 NS Cycle {cycle}: Sending '{msg}'")
        if send_message(CHANNEL_NS, msg):
            message_counts['ns'] += 1
        
        base_wait = random.randint(NS_MIN, NS_MAX)
        variance = int(base_wait * 0.1)
        wait = base_wait + random.randint(-variance, variance)
        
        log(f"🟣 NS cycle {cycle} complete. Next in {wait}s ({wait//60}m {wait%60}s)\n")
        time.sleep(wait)

# -----------------------------------
# Flask
# -----------------------------------
@app.route("/ping")
def ping():
    return "pong"

@app.route("/")
def status():
    return jsonify({'status': 'ok', 'messages': message_counts})

def run_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# -----------------------------------
# Main
# -----------------------------------
if __name__ == "__main__":
    log("🚀 Starting Discord Bot Farm")
    log(f"📍 SD Channel: {CHANNEL_SD}")
    log(f"📍 NS Channel: {CHANNEL_NS}")
    log(f"🤖 Bot ID: {BOT_A_ID}")
    
    if not TOKEN:
        log("❌ No AUTH_TOKEN found!")
        exit(1)
    
    log(f"✅ Token loaded (length: {len(TOKEN)})")
    
    threading.Thread(target=run_server, daemon=True).start()
    time.sleep(2)
    
    threading.Thread(target=sd_loop, daemon=True).start()
    threading.Thread(target=ns_loop, daemon=True).start()
    
    log("✅ All bots running!\n")
    
    while True:
        time.sleep(300)
        log(f"💓 Status - SD:{message_counts['sd']} NS:{message_counts['ns']} Clicks:{message_counts['clicks']} ClickFails:{message_counts['click_fails']}")
