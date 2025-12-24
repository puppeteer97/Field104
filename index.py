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

# Delays (longer = safer)
SD_MIN = 500  # Slightly longer than 490
SD_MAX = 620  # Slightly longer than 610
NS_MIN = 640  # Slightly longer than 630
NS_MAX = 760  # Slightly longer than 750

# Retry settings - less aggressive
MAX_RETRIES = 3  # Reduced from 5
RETRY_DELAY = 10  # Increased from 5

# -----------------------------------
# Setup
# -----------------------------------
app = Flask(__name__)
message_counts = {'sd': 0, 'ns': 0, 'clicks': 0}

# Create new session each time (less fingerprinting)
def get_session():
    s = requests.Session()
    # Mimic real browser more closely
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://discord.com/channels/@me',
        'Origin': 'https://discord.com',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
    })
    return s

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

# -----------------------------------
# Send Message (ultra-safe)
# -----------------------------------
def send_message(channel_id, msg):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    
    session = get_session()  # Fresh session each time
    headers = {
        "Authorization": TOKEN,
        "Content-Type": "application/json"
    }
    data = {"content": msg}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.post(url, headers=headers, json=data, timeout=15)
            
            # Just check status, don't parse anything
            if r.status_code in [200, 201, 204]:
                log(f"✅ Sent '{msg}'")
                return True
            elif r.status_code == 429:
                # Rate limited - back off significantly
                retry_after = 300  # Default 5 min if can't parse
                try:
                    retry_after = int(r.headers.get('Retry-After', 300))
                except:
                    pass
                log(f"⚠ Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
                return False

# -----------------------------------
# Get Messages (only for SD, very stealth)
# -----------------------------------
def get_messages_stealth(channel_id):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=3"
    
    session = get_session()
    headers = {"Authorization": TOKEN}
    
    try:
        # Random small delay before fetching
        time.sleep(random.uniform(1.5, 3.0))
        r = session.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

# -----------------------------------
# Click Button (very stealth)
# -----------------------------------
def click_button_stealth(message_id, custom_id):
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
        # Human reaction time (2-5 seconds)
        time.sleep(random.uniform(2.0, 5.0))
        r = session.post(url, headers=headers, json=payload, timeout=15)
        if r.status_code in [200, 204]:
            return True
    except:
        pass
    return False

# -----------------------------------
# Check SD Drop (stealth version)
# -----------------------------------
def check_sd_drop_stealth():
    try:
        # Wait for bot to respond (4-7 seconds)
        time.sleep(random.uniform(4.0, 7.0))
        
        messages = get_messages_stealth(CHANNEL_SD)
        
        log(f"📥 Checking {len(messages)} messages...")
        
        for msg in messages:
            # Check if from SOFI bot with "dropping"
            author_id = msg.get('author', {}).get('id')
            content = msg.get('content', '').lower()
            
            log(f"   Msg from {author_id[:10]}... content: {content[:30]}...")
            
            if author_id != BOT_A_ID:
                continue
            if 'dropping' not in content:
                continue
            
            log(f"🎴 Drop message found!")
            
            # Get buttons
            components = msg.get('components', [])
            if not components:
                log("   No components found")
                continue
            
            buttons = components[0].get('components', [])
            if not buttons:
                log("   No buttons found")
                continue
            
            log(f"   Found {len(buttons)} buttons")
            
            # Parse values quietly
            best_idx = 0
            best_val = 0
            
            for i, btn in enumerate(buttons):
                label = btn.get('label', '')
                if not label:
                    continue
                
                # Parse value
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
            
            log(f"   Best: button {best_idx} with value {best_val}")
            
            # Click quietly
            if click_button_stealth(msg['id'], buttons[best_idx].get('custom_id')):
                log(f"✅ Button clicked successfully!")
                message_counts['clicks'] += 1
            else:
                log(f"❌ Button click failed")
            
            break  # Only process first drop found
            
    except Exception as e:
        log(f"⚠️ Check error: {e}")  # Don't retry, just fail
            else:
                log(f"⚠ Status {r.status_code}")
                
        except requests.exceptions.Timeout:
            log(f"⏱ Timeout")
        except requests.exceptions.ConnectionError:
            log(f"🔌 Connection error")
        except Exception as e:
            log(f"❌ Error: {str(e)[:50]}")

        if attempt < MAX_RETRIES:
            # Exponential backoff
            wait = RETRY_DELAY * (2 ** (attempt - 1))
            log(f"🔄 Retry in {wait}s...")
            time.sleep(wait)

    return False

# -----------------------------------
# SD Loop (with stealth button clicking)
# -----------------------------------
def sd_loop():
    cycle = 0
    # Random initial delay (0-60s)
    time.sleep(random.randint(0, 60))
    
    while True:
        msg = random.choice(SD_MESSAGES)
        
        if send_message(CHANNEL_SD, msg):
            message_counts['sd'] += 1
            
            # Only check for drops 70% of the time (more human)
            if random.random() < 0.7:
                try:
                    check_sd_drop_stealth()
                except:
                    pass  # Fail silently
        
        cycle += 1
        # Add extra variance (±10%)
        base_wait = random.randint(SD_MIN, SD_MAX)
        variance = int(base_wait * 0.1)
        wait = base_wait + random.randint(-variance, variance)
        
        log(f"🔵 SD cycle {cycle}. Next in {wait}s")
        time.sleep(wait)

# -----------------------------------
# NS Loop (messages only, no clicking)
# -----------------------------------
def ns_loop():
    cycle = 0
    # Random initial delay (0-90s)
    time.sleep(random.randint(0, 90))
    
    while True:
        msg = random.choice(NS_MESSAGES)
        
        if send_message(CHANNEL_NS, msg):
            message_counts['ns'] += 1
        
        cycle += 1
        # Add extra variance (±10%)
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
    return jsonify({
        'status': 'ok',
        'messages': message_counts
    })

def run_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# -----------------------------------
# Main
# -----------------------------------
if __name__ == "__main__":
    log("🚀 Starting stealth bot")
    
    if not TOKEN:
        log("❌ No token")
        exit(1)
    
    # Start Flask
    threading.Thread(target=run_server, daemon=True).start()
    time.sleep(2)
    
    # Start loops
    threading.Thread(target=sd_loop, daemon=True).start()
    threading.Thread(target=ns_loop, daemon=True).start()
    
    log("✅ Running")
    
    # Keep alive
    while True:
        time.sleep(300)  # Log every 5 min instead of 1 min
        log(f"💓 SD:{message_counts['sd']} NS:{message_counts['ns']} Clicks:{message_counts['clicks']}")
