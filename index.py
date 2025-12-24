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

# Bot A (SD) - with button clicking
BOT_A_ID = '853629533855809596'
CHANNEL_SD = '1452336850415915133'
GUILD_ID = '1452333704062959677'
SD_MESSAGES = ['SD', 'sd', 'Sd', 'sD']
SD_MIN = 490
SD_MAX = 610

# Bot B (NS) - message only
CHANNEL_NS = '1453016616185892986'
NS_MESSAGES = ['ns', 'NS', 'Ns', 'nS']
NS_MIN = 630
NS_MAX = 750

MAX_RETRIES = 5
RETRY_DELAY = 5

# -----------------------------------
# Setup
# -----------------------------------
app = Flask(__name__)
session = requests.Session()
message_counts = {'sd': 0, 'ns': 0, 'clicks': 0}

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

# -----------------------------------
# Send Message (ONLY ACTION)
# -----------------------------------
def send_message(channel_id, msg):
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": TOKEN,
        "Content-Type": "application/json"
    }
    data = {"content": msg}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.post(url, headers=headers, json=data, timeout=10)
            
            # Don't parse JSON, just check status
            if r.status_code in [200, 204]:
                log(f"✅ Sent '{msg}' to channel {channel_id}")
                return True
            elif r.status_code == 429:
                retry_after = int(r.headers.get('Retry-After', 60))
                log(f"⚠ Rate limited. Retrying after {retry_after}s...")
                time.sleep(retry_after)
            else:
                log(f"⚠ Status {r.status_code}")
                
        except requests.exceptions.Timeout:
            log(f"⏱ Timeout on attempt {attempt}")
        except requests.exceptions.ConnectionError:
            log(f"🔌 Connection error on attempt {attempt}")
        except Exception as e:
            log(f"❌ Error on attempt {attempt}: {e}")

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    log(f"❌ Failed to send '{msg}' after {MAX_RETRIES} attempts")
    return False

# -----------------------------------
# Get Messages (minimal, for SD bot only)
# -----------------------------------
def get_recent_messages(channel_id, limit=5):
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit={limit}"
    headers = {"Authorization": TOKEN}
    
    try:
        r = session.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

# -----------------------------------
# Click Button (minimal, for SD bot only)
# -----------------------------------
def click_button(message_id, channel_id, custom_id):
    url = "https://discord.com/api/v10/interactions"
    headers = {
        "Authorization": TOKEN,
        "Content-Type": "application/json"
    }
    payload = {
        "type": 3,
        "guild_id": GUILD_ID,
        "channel_id": channel_id,
        "message_id": message_id,
        "data": {"component_type": 2, "custom_id": custom_id}
    }
    
    try:
        time.sleep(random.uniform(0.5, 1.5))  # Human delay
        r = session.post(url, headers=headers, json=payload, timeout=10)
        if r.status_code in [200, 204]:
            return True
    except:
        pass
    return False

# -----------------------------------
# Check SD Drops (minimal logic)
# -----------------------------------
def check_sd_drop(our_msg_id):
    try:
        time.sleep(3)  # Wait for bot to respond
        messages = get_recent_messages(CHANNEL_SD, 5)
        
        for msg in messages:
            # Check if it's from SOFI bot, has "dropping", and replies to us
            if (msg.get('author', {}).get('id') != BOT_A_ID or
                'dropping' not in msg.get('content', '').lower() or
                msg.get('referenced_message', {}).get('id') != our_msg_id):
                continue
            
            # Get buttons
            buttons = msg.get('components', [{}])[0].get('components', [])
            if not buttons:
                continue
            
            # Parse values
            def parse_val(label):
                if not label:
                    return 0
                label = str(label).lower().strip()
                if 'k' in label:
                    try:
                        return int(float(label.replace('k', '')) * 1000)
                    except:
                        return 0
                try:
                    return int(label)
                except:
                    return 0
            
            # Find highest
            best_idx = 0
            best_val = 0
            for i, btn in enumerate(buttons):
                val = parse_val(btn.get('label', ''))
                if val > best_val:
                    best_val = val
                    best_idx = i
            
            log(f"🎴 Drop found! Clicking button {best_idx} (value: {best_val})")
            
            if click_button(msg['id'], CHANNEL_SD, buttons[best_idx].get('custom_id')):
                log("✅ Button clicked!")
                message_counts['clicks'] += 1
            break
            
    except Exception as e:
        log(f"⚠️ Check drop error: {e}")

# -----------------------------------
# SD Loop (with button clicking)
# -----------------------------------
def sd_loop():
    cycle = 0
    while True:
        msg = random.choice(SD_MESSAGES)
        success = send_message(CHANNEL_SD, msg)
        
        if success:
            message_counts['sd'] += 1
            # Try to check for drops (won't crash if it fails)
            try:
                check_sd_drop(None)  # We don't have message ID, so check recent
            except:
                pass
        
        cycle += 1
        wait = random.randint(SD_MIN, SD_MAX)
        log(f"🔵 SD cycle {cycle} done. Waiting {wait}s...")
        time.sleep(wait)

# -----------------------------------
# NS Loop
# -----------------------------------
def ns_loop():
    cycle = 0
    while True:
        msg = random.choice(NS_MESSAGES)
        if send_message(CHANNEL_NS, msg):
            message_counts['ns'] += 1
        
        cycle += 1
        wait = random.randint(NS_MIN, NS_MAX)
        log(f"🟣 NS cycle {cycle} done. Waiting {wait}s...")
        time.sleep(wait)

# -----------------------------------
# Flask
# -----------------------------------
@app.route("/ping")
def ping():
    return "OK"

@app.route("/")
def status():
    return jsonify(message_counts)

def run_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# -----------------------------------
# Main
# -----------------------------------
if __name__ == "__main__":
    log("🚀 Starting minimal bot (messages only)")
    
    if not TOKEN:
        log("❌ No token!")
        exit(1)
    
    # Start Flask
    threading.Thread(target=run_server, daemon=True).start()
    time.sleep(1)
    
    # Start SD
    threading.Thread(target=sd_loop, daemon=True).start()
    log("✅ SD loop started")
    
    # Start NS
    threading.Thread(target=ns_loop, daemon=True).start()
    log("✅ NS loop started")
    
    # Keep alive
    while True:
        time.sleep(60)
