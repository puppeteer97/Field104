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
sys.stdout.reconfigure(line_buffering=True)
os.environ['PYTHONUNBUFFERED'] = '1'

# -----------------------------------
# Configuration
# -----------------------------------
TOKEN = os.environ.get("AUTH_TOKEN", "").strip()

# Bot A (SD)
BOT_A_ID = '853629533855809596'
BOT_A_CHANNEL_ID = '1452336850415915133'
BOT_A_GUILD_ID = '1452333704062959677'
SD_MIN = 60  # Changed to 60 seconds for testing
SD_MAX = 90  # Changed to 90 seconds for testing
SD_MESSAGES = ['SD', 'sd', 'Sd', 'sD']

# Bot B (NS)
BOT_B_ID = '1312830013573169252'
BOT_B_CHANNEL_ID = '1453016616185892986'
BOT_B_GUILD_ID = '1452333704062959677'
NS_MIN = 60  # Changed to 60 seconds for testing
NS_MAX = 90  # Changed to 90 seconds for testing
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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

def send_message(channel_id, content):
    url = f'https://discord.com/api/v9/channels/{channel_id}/messages'
    
    for attempt in range(1, 6):
        try:
            r = session.post(url, headers=get_headers(), json={'content': content}, timeout=10)
            
            if r.status_code in [200, 204]:
                log(f'✅ Sent: {content}')
                return r.json() if r.text else {}
            elif r.status_code == 429:
                retry_after = r.json().get('retry_after', 60)
                log(f'⚠️ Rate limited. Waiting {retry_after}s...')
                time.sleep(retry_after)
            else:
                log(f'⚠️ HTTP {r.status_code}')
                
        except Exception as e:
            log(f'⚠️ Error attempt {attempt}: {e}')
        
        if attempt < 5:
            time.sleep(5)
    
    message_counts['errors'] += 1
    return None

def get_messages(channel_id, limit=10):
    url = f'https://discord.com/api/v9/channels/{channel_id}/messages?limit={limit}'
    try:
        r = session.get(url, headers=get_headers(), timeout=10)
        return r.json() if r.status_code == 200 else []
    except:
        return []

def click_button(message_id, channel_id, custom_id, guild_id):
    url = 'https://discord.com/api/v9/interactions'
    
    time.sleep(random.uniform(0.3, 1.2))  # Human delay
    
    payload = {
        'type': 3,
        'guild_id': guild_id,
        'channel_id': channel_id,
        'message_id': message_id,
        'data': {
            'component_type': 2,
            'custom_id': custom_id
        }
    }
    
    try:
        r = session.post(url, headers=get_headers(), json=payload, timeout=10)
        if r.status_code in [200, 204]:
            return True
        else:
            log(f'⚠️ Button click failed: HTTP {r.status_code} - {r.text[:200]}')
            return False
    except Exception as e:
        log(f'⚠️ Button click exception: {e}')
        return False

# -----------------------------------
# Bot A Logic (SD)
# -----------------------------------
def check_bot_a_drops(our_message_id):
    try:
        time.sleep(1)  # Give bot time to respond
        messages = get_messages(BOT_A_CHANNEL_ID, 5)
        
        log(f'[BOT-A] Checking {len(messages)} recent messages...')
        
        for msg in messages:
            if msg['author']['id'] != BOT_A_ID:
                continue
            if 'dropping' not in msg['content'].lower():
                continue
            if msg.get('referenced_message', {}).get('id') != our_message_id:
                continue
            
            log('[BOT-A] 🎴 Drop detected!')
            
            if not msg.get('components'):
                continue
            
            buttons = msg['components'][0]['components']
            
            # Parse values
            def parse_value(label):
                if not label:
                    return 0
                label = label.lower().strip()
                if 'k' in label:
                    return int(float(label.replace('k', '')) * 1000)
                try:
                    return int(label)
                except:
                    return 0
            
            button_data = [(i, parse_value(btn.get('label', '')), btn.get('custom_id')) 
                          for i, btn in enumerate(buttons)]
            
            max_button = max(button_data, key=lambda x: x[1])
            log(f'[BOT-A] ✅ Clicking button {max_button[0]} (value: {max_button[1]})')
            
            if click_button(msg['id'], BOT_A_CHANNEL_ID, max_button[2], BOT_A_GUILD_ID):
                log('[BOT-A] 🎉 Success!')
            break
    except Exception as e:
        log(f'[BOT-A] ⚠️ Error: {e}')

def bot_a_loop():
    cycle = 0
    while True:
        try:
            cycle += 1
            msg = random.choice(SD_MESSAGES)
            
            log(f'[BOT-A] 📤 Cycle {cycle}: {msg}')
            sent = send_message(BOT_A_CHANNEL_ID, msg)
            
            if sent:
                message_counts['botA'] += 1
                time.sleep(3)
                if 'id' in sent:
                    check_bot_a_drops(sent['id'])
            else:
                log('[BOT-A] ⚠️ Message send failed')
                
        except Exception as e:
            log(f'[BOT-A] ❌ Loop error: {e}')
            import traceback
            log(traceback.format_exc())
        
        wait = random.randint(SD_MIN, SD_MAX)
        log(f'[BOT-A] ⏰ Next in {wait} seconds\n')
        time.sleep(wait)

# -----------------------------------
# Bot B Logic (NS)
# -----------------------------------
def check_bot_b_drops(our_message_id):
    try:
        time.sleep(1)  # Give bot time to respond
        messages = get_messages(BOT_B_CHANNEL_ID, 10)
        
        log(f'[BOT-B] Checking {len(messages)} recent messages...')
        
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
        
        log('[BOT-B] 🎴 Drop detected!')
        
        # Parse WL values
        lines = stats_msg['content'].split('\n')
        card_values = []
        
        for line in lines:
            match = re.search(r'`\s*(\d+)`\s*<:nwl_s:', line)
            if match:
                card_values.append(int(match.group(1)))
        
        if not card_values:
            return
        
        max_value = max(card_values)
        highest_index = card_values.index(max_value)
        
        log(f'[BOT-B] ✅ Clicking button {highest_index + 1} (value: {max_value})')
        
        buttons = button_msg['components'][0]['components']
        if click_button(button_msg['id'], BOT_B_CHANNEL_ID, buttons[highest_index]['custom_id'], BOT_B_GUILD_ID):
            log('[BOT-B] 🎉 Success!')
            
    except Exception as e:
        log(f'[BOT-B] ⚠️ Error: {e}')

def bot_b_loop():
    cycle = 0
    while True:
        try:
            cycle += 1
            msg = random.choice(NS_MESSAGES)
            
            log(f'[BOT-B] 📤 Cycle {cycle}: {msg}')
            sent = send_message(BOT_B_CHANNEL_ID, msg)
            
            if sent:
                message_counts['botB'] += 1
                time.sleep(3)
                if 'id' in sent:
                    check_bot_b_drops(sent['id'])
            else:
                log('[BOT-B] ⚠️ Message send failed')
                
        except Exception as e:
            log(f'[BOT-B] ❌ Loop error: {e}')
            import traceback
            log(traceback.format_exc())
        
        wait = random.randint(NS_MIN, NS_MAX)
        log(f'[BOT-B] ⏰ Next in {wait} seconds\n')
        time.sleep(wait)

# -----------------------------------
# Flask Routes
# -----------------------------------
@app.route('/')
def home():
    uptime = int((time.time() - start_time) / 60)
    return jsonify({
        'status': 'alive',
        'uptime_minutes': uptime,
        'messages': message_counts
    })

@app.route('/ping')
def ping():
    return 'pong'

@app.route('/stats')
def stats():
    return jsonify(message_counts)

def run_server():
    port = int(os.environ.get('PORT', 10000))
    log(f'🌐 Flask starting on port {port}')
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# -----------------------------------
# Main
# -----------------------------------
if __name__ == '__main__':
    print('🚀 Starting Discord Bot', flush=True)
    
    if not TOKEN:
        print('❌ AUTH_TOKEN missing!', flush=True)
        exit(1)
    
    print(f'✅ Token: {TOKEN[:15]}...{TOKEN[-10:]}', flush=True)
    print('---CHECKPOINT 1---', flush=True)    print('---CHECKPOINT 1---', flush=True)
    
    # Start bots FIRST
    print('[BOT-A] 🔵 Starting SD bot thread...', flush=True)
    bot_a_thread = threading.Thread(target=bot_a_loop, daemon=True)
    bot_a_thread.start()
    print(f'[BOT-A] Thread alive: {bot_a_thread.is_alive()}', flush=True)
    
    print('[BOT-B] 🔵 Starting NS bot thread...', flush=True)
    bot_b_thread = threading.Thread(target=bot_b_loop, daemon=True)
    bot_b_thread.start()
    print(f'[BOT-B] Thread alive: {bot_b_thread.is_alive()}', flush=True)
    
    print('✅ Bot threads started\n', flush=True)
    print('---CHECKPOINT 2---', flush=True)
    
    # Start Flask LAST in daemon thread
    print('🌐 Starting Flask in background...', flush=True)
    threading.Thread(target=run_server, daemon=True).start()
    
    time.sleep(2)
    print('✅ Flask started\n', flush=True)
    print('---CHECKPOINT 3---', flush=True)
    
    # Keep alive
    print('♾️ Main loop running...', flush=True)
    while True:
        time.sleep(60)
        uptime = int((time.time() - start_time) / 60)
        log(f'💓 Uptime: {uptime}m | A:{message_counts["botA"]} B:{message_counts["botB"]} E:{message_counts["errors"]}')
