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
message_counts = {'sd': 0, 'ns': 0, 'clicks': 0}

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
                log(f"✅ Sent '{msg}'")
                return True
            elif r.status_code == 429:
                retry_after = 300
                try:
                    retry_after = int(r.headers.get('Retry-After', 300))
                except:
                    pass
                log(f"⚠ Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
                return False
            else:
                log(f"⚠ Status {r.status_code}")
                
        except Exception as e:
            log(f"❌ Error: {str(e)[:50]}")

        if attempt < MAX_RETRIES:
            wait = RETRY_DELAY * (2 ** (attempt - 1))
            time.sleep(wait)

    return False

# -----------------------------------
# Get Messages
# -----------------------------------
def get_messages(channel_id):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=3"
    session = get_session()
    headers = {"Authorization": TOKEN}
    
    try:
        time.sleep(random.uniform(1.5, 3.0))
        r = session.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

# -----------------------------------
# Click Button
# -----------------------------------
def click_button(message_id, custom_id):
    url = "https://discord.com/api/v9/interactions"
    session = get_session()
    headers = {
        "Authorization": TOKEN,
        "Content-Type": "application/json"
    }
    payload = {
        "type": 3,
        "guild_id": GUILD_ID,
        "channel_id": CHANNEL_SD,
        "message_id": message_id,
        "data": {"component_type": 2, "custom_id": custom_id}
    }
    
    try:
        time.sleep(random.uniform(2.0, 5.0))
        r = session.post(url, headers=headers, json=payload, timeout=15)
        if r.status_code in [200, 204]:
            return True
    except:
        pass
    return False

# -----------------------------------
# Check SD Drop
# -----------------------------------
def check_sd_drop():
    try:
        time.sleep(random.uniform(4.0, 7.0))
        messages = get_messages(CHANNEL_SD)
        
        log(f"📥 Checking {len(messages)} messages...")
        
        for msg in messages:
            author_id = msg.get('author', {}).get('id')
            content = msg.get('content', '').lower()
            
            if author_id != BOT_A_ID:
                continue
            if 'dropping' not in content:
                continue
            
            log(f"🎴 Drop found!")
            
            components = msg.get('components', [])
            if not components:
                log("   No components")
                continue
            
            buttons = components[0].get('components', [])
            if not buttons:
                log("   No buttons")
                continue
            
            log(f"   Found {len(buttons)} buttons")
            
            best_idx = 0
            best_val = 0
            
            for i, btn in enumerate(buttons):
                label = btn.get('label', '')
                val = 0
                try:
                    label_str = str(label).lower().strip()
                    if 'k' in label_str:
                        val = int(float(label_str.replace('k', '')) * 1000)
                    else:
                        val = int(label_str)
                except:
                    val = 0
                
                log(f"   Button {i}: {label} = {val}")
                
                if val > best_val:
                    best_val = val
                    best_idx = i
            
            log(f"   Clicking button {best_idx} (value: {best_val})")
            
            if click_button(msg['id'], buttons[best_idx].get('custom_id')):
                log(f"✅ Button clicked!")
                message_counts['clicks'] += 1
            else:
                log(f"❌ Click failed")
            
            break
            
    except Exception as e:
        log(f"⚠️ Check error: {e}")

# -----------------------------------
# SD Loop
# -----------------------------------
def sd_loop():
    cycle = 0
    time.sleep(random.randint(0, 60))
    
    while True:
        msg = random.choice(SD_MESSAGES)
        
        if send_message(CHANNEL_SD, msg):
            message_counts['sd'] += 1
            
            if random.random() < 0.7:
                try:
                    check_sd_drop()
                except Exception as e:
                    log(f"⚠️ Drop check failed: {e}")
        
        cycle += 1
        base_wait = random.randint(SD_MIN, SD_MAX)
        variance = int(base_wait * 0.1)
        wait = base_wait + random.randint(-variance, variance)
        
        log(f"🔵 SD cycle {cycle}. Next in {wait}s")
        time.sleep(wait)

# -----------------------------------
# NS Loop
# -----------------------------------
def ns_loop():
    cycle = 0
    time.sleep(random.randint(0, 90))
    
    while True:
        msg = random.choice(NS_MESSAGES)
        
        if send_message(CHANNEL_NS, msg):
            message_counts['ns'] += 1
        
        cycle += 1
        base_wait = random.randint(NS_MIN, NS_MAX)
        variance = int(base_wait * 0.1)
        wait = base_wait + random.randint(-variance, variance)
        
        log(f"🟣 NS cycle {cycle}. Next in {wait}s")
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
    log("🚀 Starting bot")
    
    if not TOKEN:
        log("❌ No token")
        exit(1)
    
    threading.Thread(target=run_server, daemon=True).start()
    time.sleep(2)
    
    threading.Thread(target=sd_loop, daemon=True).start()
    threading.Thread(target=ns_loop, daemon=True).start()
    
    log("✅ Running")
    
    while True:
        time.sleep(300)
        log(f"💓 SD:{message_counts['sd']} NS:{message_counts['ns']} Clicks:{message_counts['clicks']}")
