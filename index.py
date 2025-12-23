import requests
import time
import random
import os
import sys
import threading
import re
from datetime import datetime
from flask import Flask, jsonify

# Force unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'

# -----------------------------------
# Configuration
# -----------------------------------
TOKEN = os.environ.get("AUTH_TOKEN", "").strip()

# Bot A (SD)
BOT_A_ID = '853629533855809596'
BOT_A_CHANNEL_ID = '1452336850415915133'
BOT_A_GUILD_ID = '1452333704062959677'
SD_MIN = 60
SD_MAX = 90
SD_MESSAGES = ['SD', 'sd', 'Sd', 'sD']

# Bot B (NS)
BOT_B_ID = '1312830013573169252'
BOT_B_CHANNEL_ID = '1453016616185892986'
BOT_B_GUILD_ID = '1452333704062959677'
NS_MIN = 60
NS_MAX = 90
NS_MESSAGES = ['ns', 'NS', 'Ns', 'nS']

# -----------------------------------
# Setup
# -----------------------------------
app = Flask(__name__)
session = requests.Session()
message_counts = {'botA': 0, 'botB': 0, 'errors': 0}
start_time = time.time()

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

# -----------------------------------
# Discord API Functions
# -----------------------------------
def get_headers():
    return {
        'Authorization': TOKEN,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }

def send_message(channel_id, content):
    url = f'https://discord.com/api/v9/channels/{channel_id}/messages'
    
    for attempt in range(1, 4):
        try:
            r = session.post(url, headers=get_headers(), json={'content': content}, timeout=10)
            
            if r.status_code in [200, 204]:
                try:
                    return r.json()
                except Exception:
                    log(f'⚠️ Non-JSON success response: {r.text[:200]}')
                    return {}
            else:
                log(f'⚠️ HTTP {r.status_code}: {r.text[:200]}')
                
            if r.status_code == 429:
                retry_after = r.json().get('retry_after', 60)
                log(f'Rate limited, waiting {retry_after}s')
                time.sleep(retry_after)
            elif r.status_code in [401, 403]:
                log(f'🚫 AUTH ERROR! TOKEN IS INVALID OR EXPIRED')
                return None
                
        except Exception as e:
            log(f'⚠️ Exception: {e}')
        
        if attempt < 3:
            time.sleep(3)
    
    message_counts['errors'] += 1
    return None

def get_messages(channel_id, limit=10):
    url = f'https://discord.com/api/v9/channels/{channel_id}/messages?limit={limit}'
    try:
        r = session.get(url, headers=get_headers(), timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            log(f'⚠️ Get messages HTTP {r.status_code}: {r.text[:200]}')
            return []
    except Exception as e:
        log(f'⚠️ Get messages error: {e}')
        return []

def click_button(message_id, channel_id, custom_id, guild_id):
    url = 'https://discord.com/api/v9/interactions'
    time.sleep(random.uniform(0.3, 1.0))
    
    payload = {
        'type': 3,
        'guild_id': guild_id,
        'channel_id': channel_id,
        'message_id': message_id,
        'data': {'component_type': 2, 'custom_id': custom_id}
    }
    
    try:
        r = session.post(url, headers=get_headers(), json=payload, timeout=10)
        if r.status_code in [200, 204]:
            return True
        log(f'⚠️ Button click HTTP {r.status_code}: {r.text[:200]}')
        return False
    except Exception as e:
        log(f'⚠️ Button error: {e}')
        return False

# -----------------------------------
# Bot A Logic
# -----------------------------------
def check_bot_a_drops(our_message_id):
    try:
        time.sleep(2)
        messages = get_messages(BOT_A_CHANNEL_ID, 5)
        
        for msg in messages:
            if msg['author']['id'] != BOT_A_ID:
                continue
            if 'dropping' not in msg['content'].lower():
                continue
            if msg.get('referenced_message', {}).get('id') != our_message_id:
                continue
            
            log('[BOT-A] 🎴 Drop found!')
            
            if not msg.get('components'):
                continue
            
            buttons = msg['components'][0]['components']
            
            def parse_val(label):
                if not label:
                    return 0
                label = label.lower().strip()
                if 'k' in label:
                    return int(float(label.replace('k', '')) * 1000)
                return int(label) if label.isdigit() else 0
            
            best = max(enumerate(buttons), key=lambda x: parse_val(x[1].get('label', '')))
            log(f'[BOT-A] Clicking button {best[0]}')
            
            if click_button(msg['id'], BOT_A_CHANNEL_ID, best[1]['custom_id'], BOT_A_GUILD_ID):
                log('[BOT-A] 🎉 Clicked!')
            break
    except Exception as e:
        log(f'[BOT-A] Check error: {e}')

def bot_a_loop():
    cycle = 0
    while True:
        try:
            cycle += 1
            msg = random.choice(SD_MESSAGES)
            log(f'[BOT-A] Cycle {cycle}: {msg}')
            
            sent = send_message(BOT_A_CHANNEL_ID, msg)
            if sent:
                message_counts['botA'] += 1
                log(f'[BOT-A] ✅ Message sent successfully')
                if 'id' in sent:
                    check_bot_a_drops(sent['id'])
            else:
                log(f'[BOT-A] ❌ Failed to send message')
        except Exception as e:
            log(f'[BOT-A] Loop error: {e}')
        
        wait = random.randint(SD_MIN, SD_MAX)
        log(f'[BOT-A] Next in {wait}s\n')
        time.sleep(wait)

# -----------------------------------
# Bot B Logic
# -----------------------------------
def check_bot_b_drops(our_message_id):
    try:
        time.sleep(2)
        messages = get_messages(BOT_B_CHANNEL_ID, 10)
        
        button_msg = None
        stats_msg = None
        
        for msg in messages:
            if msg['author']['id'] != BOT_B_ID:
                continue
            if msg.get('components'):
                button_msg = msg
            if msg.get('reference') and '¦' in msg['content']:
                if button_msg and msg['reference'].get('message_id') == button_msg['id']:
                    stats_msg = msg
                    break
        
        if not button_msg or not stats_msg:
            return
        
        log('[BOT-B] 🎴 Drop found!')
        
        card_values = []
        for line in stats_msg['content'].split('\n'):
            match = re.search(r'`\s*(\d+)`\s*<:nwl_s:', line)
            if match:
                card_values.append(int(match.group(1)))
        
        if not card_values:
            return
        
        highest_idx = card_values.index(max(card_values))
        log(f'[BOT-B] Clicking button {highest_idx + 1}')
        
        buttons = button_msg['components'][0]['components']
        if click_button(button_msg['id'], BOT_B_CHANNEL_ID, buttons[highest_idx]['custom_id'], BOT_B_GUILD_ID):
            log('[BOT-B] 🎉 Clicked!')
            
    except Exception as e:
        log(f'[BOT-B] Check error: {e}')

def bot_b_loop():
    cycle = 0
    while True:
        try:
            cycle += 1
            msg = random.choice(NS_MESSAGES)
            log(f'[BOT-B] Cycle {cycle}: {msg}')
            
            sent = send_message(BOT_B_CHANNEL_ID, msg)
            if sent:
                message_counts['botB'] += 1
                log(f'[BOT-B] ✅ Message sent successfully')
                if 'id' in sent:
                    check_bot_b_drops(sent['id'])
            else:
                log(f'[BOT-B] ❌ Failed to send message')
        except Exception as e:
            log(f'[BOT-B] Loop error: {e}')
        
        wait = random.randint(NS_MIN, NS_MAX)
        log(f'[BOT-B] Next in {wait}s\n')
        time.sleep(wait)

# -----------------------------------
# Flask
# -----------------------------------
@app.route('/')
def home():
    return jsonify({'status': 'alive', 'messages': message_counts})

@app.route('/ping')
def ping():
    return 'pong'

@app.route('/stats')
def stats():
    return jsonify(message_counts)

def run_server():
    port = int(os.environ.get('PORT', 10000))
    log(f'Flask on port {port}')
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# -----------------------------------
# Main
# -----------------------------------
if __name__ == '__main__':
    log('Starting bot')
    
    if not TOKEN:
        log('No token!')
        exit(1)
    
    log(f'Token OK: {TOKEN[:10]}...')
    
    # Start bots
    log('Starting BOT-A...')
    threading.Thread(target=bot_a_loop, daemon=True).start()
    
    log('Starting BOT-B...')
    threading.Thread(target=bot_b_loop, daemon=True).start()
    
    # Start Flask
    log('Starting Flask...')
    threading.Thread(target=run_server, daemon=True).start()
    
    time.sleep(3)
    log('All running!\n')
    
    # Keep alive
    while True:
        time.sleep(60)
        log(f'Alive | A:{message_counts["botA"]} B:{message_counts["botB"]} E:{message_counts["errors"]}')
