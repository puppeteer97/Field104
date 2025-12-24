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
BOT_B_ID = '1312830013573169252'
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
                log(f"✅ Sent '{msg}'")
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
                log(f"⚠ Status {r.status_code}")
                
        except Exception as e:
            log(f"❌ Send error: {str(e)[:100]}")

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
    except:
        pass
    return []

# -----------------------------------
# Click Button - FIXED
# -----------------------------------
def click_button(message_id, channel_id, custom_id, button_index, value, bot_id):
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
        "application_id": bot_id,
        "session_id": "1234567890abcdef",
        "data": {
            "component_type": 2,
            "custom_id": custom_id
        }
    }
    
    log(f"🔘 Clicking button {button_index} (value: {value})")
    
    try:
        delay = random.uniform(1.5, 3.5)
        time.sleep(delay)
        
        r = session.post(url, headers=headers, json=payload, timeout=15)
        
        if r.status_code in [200, 204]:
            log(f"✅ Button clicked successfully!")
            return True
        else:
            log(f"❌ Click failed: {r.status_code} - {r.text[:200]}")
            
    except Exception as e:
        log(f"❌ Click error: {e}")
    
    return False

# -----------------------------------
# Check SD Drop
# -----------------------------------
def check_sd_drop():
    try:
        log("🔍 Checking SD drops...")
        messages = get_messages(CHANNEL_SD)
        
        for msg in messages:
            author_id = msg.get('author', {}).get('id')
            content = msg.get('content', '')
            
            if author_id != BOT_A_ID:
                continue
            if 'dropping' not in content.lower():
                continue
            
            components = msg.get('components', [])
            if not components:
                continue
            
            log(f"🎴 Drop found!")
            
            buttons = components[0].get('components', [])
            if not buttons:
                continue
            
            button_data = []
            for idx, btn in enumerate(buttons):
                label = btn.get('label', '')
                custom_id = btn.get('custom_id', '')
                
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
                    'value': val,
                    'custom_id': custom_id
                })
                
                log(f"   Button {idx}: Value={val}")
            
            best = max(button_data, key=lambda x: x['value'])
            log(f"🎯 Highest: Button {best['index']} = {best['value']}")
            
            success = click_button(
                msg['id'],
                CHANNEL_SD,
                best['custom_id'],
                best['index'],
                best['value'],
                BOT_A_ID
            )
            
            if success:
                message_counts['clicks'] += 1
            else:
                message_counts['click_fails'] += 1
            
            break
            
    except Exception as e:
        log(f"⚠️ SD check error: {e}")

# -----------------------------------
# Check NS Drop
# -----------------------------------
def check_ns_drop():
    try:
        log("🔍 Checking NS drops...")
        messages = get_messages(CHANNEL_NS)
        
        button_msg = None
        stats_msg = None
        
        for msg in messages:
            if msg.get('author', {}).get('id') != BOT_B_ID:
                continue
            
            if msg.get('components'):
                button_msg = msg
            
            if msg.get('content') and '¦' in msg.get('content', ''):
                stats_msg = msg
        
        if not button_msg or not stats_msg:
            return
        
        log(f"🎴 NS drop found!")
        
        import re
        lines = stats_msg['content'].split('\n')
        values = []
        
        for line in lines:
            match = re.search(r'`\s*(\d+)`\s*<:nwl_s:', line)
            if match:
                values.append(int(match.group(1)))
        
        log(f"   Values: {values}")
        
        if not values:
            return
        
        max_val = max(values)
        max_idx = values.index(max_val)
        
        log(f"🎯 Highest: Button {max_idx} = {max_val}")
        
        buttons = button_msg['components'][0]['components']
        
        success = click_button(
            button_msg['id'],
            CHANNEL_NS,
            buttons[max_idx]['custom_id'],
            max_idx,
            max_val,
            BOT_B_ID
        )
        
        if success:
            message_counts['clicks'] += 1
        else:
            message_counts['click_fails'] += 1
            
    except Exception as e:
        log(f"⚠️ NS check error: {e}")

# -----------------------------------
# SD Loop
# -----------------------------------
def sd_loop():
    cycle = 0
    initial = random.randint(5, 30)
    log(f"🔵 SD starting in {initial}s")
    time.sleep(initial)
    
    while True:
        cycle += 1
        msg = random.choice(SD_MESSAGES)
        
        log(f"🔵 SD #{cycle}: '{msg}'")
        sent = send_message(CHANNEL_SD, msg)
        
        if sent:
            message_counts['sd'] += 1
            check_sd_drop()
        
        wait = random.randint(SD_MIN, SD_MAX)
        wait += random.randint(-int(wait*0.1), int(wait*0.1))
        
        log(f"🔵 Next SD in {wait}s ({wait//60}m)\n")
        time.sleep(wait)

# -----------------------------------
# NS Loop
# -----------------------------------
def ns_loop():
    cycle = 0
    initial = random.randint(10, 40)
    log(f"🟣 NS starting in {initial}s")
    time.sleep(initial)
    
    while True:
        cycle += 1
        msg = random.choice(NS_MESSAGES)
        
        log(f"🟣 NS #{cycle}: '{msg}'")
        sent = send_message(CHANNEL_NS, msg)
        
        if sent:
            message_counts['ns'] += 1
            check_ns_drop()
        
        wait = random.randint(NS_MIN, NS_MAX)
        wait += random.randint(-int(wait*0.1), int(wait*0.1))
        
        log(f"🟣 Next NS in {wait}s ({wait//60}m)\n")
        time.sleep(wait)

# -----------------------------------
# Flask
# -----------------------------------
@app.route("/ping")
def ping():
    return "pong"

@app.route("/")
def status():
    return jsonify({'status': 'ok', 'stats': message_counts})

def run_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# -----------------------------------
# Main
# -----------------------------------
if __name__ == "__main__":
    log("🚀 Discord Bot Farm Starting")
    log(f"📍 SD: {CHANNEL_SD}")
    log(f"📍 NS: {CHANNEL_NS}")
    
    if not TOKEN:
        log("❌ No token!")
        exit(1)
    
    log(f"✅ Token OK ({len(TOKEN)} chars)\n")
    
    threading.Thread(target=run_server, daemon=True).start()
    time.sleep(2)
    
    threading.Thread(target=sd_loop, daemon=True).start()
    threading.Thread(target=ns_loop, daemon=True).start()
    
    log("✅ All bots running!\n")
    
    while True:
        time.sleep(300)
        log(f"💓 SD:{message_counts['sd']} NS:{message_counts['ns']} ✅:{message_counts['clicks']} ❌:{message_counts['click_fails']}")
