import requests
import time
import random
import os
import threading
import json
from datetime import datetime
from flask import Flask, jsonify

# -----------------------------------
# Configuration from environment
# -----------------------------------
TOKEN = os.environ.get("AUTH_TOKEN", "").strip().strip('"').strip("'")

print('🔍 Checking AUTH_TOKEN...')
if not TOKEN:
    print('❌ AUTH_TOKEN environment variable is not set!')
    exit(1)
else:
    print('✅ AUTH_TOKEN found')
    print(f'📏 Token length: {len(TOKEN)} characters')
    print(f'🔤 Token preview: {TOKEN[:15]}...{TOKEN[-10:]}')

# Bot A Configuration (SD)
BOT_A_ID = '853629533855809596'
BOT_A_CHANNEL_ID = '1452336850415915133'
BOT_A_GUILD_ID = '1452333704062959677'  # Add your server/guild ID here
CMD_A_MIN_DELAY = 490  # seconds
CMD_A_MAX_DELAY = 610  # seconds
CMD_A_VARIANTS = ['SD', 'sd', 'Sd', 'sD']

# Bot B Configuration (NS)
BOT_B_ID = '1312830013573169252'
BOT_B_CHANNEL_ID = '1453016616185892986'
BOT_B_GUILD_ID = '1452333704062959677'  # Add your server/guild ID here
CMD_B_MIN_DELAY = 630  # seconds
CMD_B_MAX_DELAY = 750  # seconds
CMD_B_VARIANTS = ['ns', 'NS', 'Ns', 'nS']

# Retry settings
MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds

# Message tracking
message_counts = {
    'botA': 0,
    'botB': 0,
    'errors': 0
}

# Session for connection pooling
session = requests.Session()
cookie_jar = {}

# -----------------------------------
# Utility Functions
# -----------------------------------
def log(msg):
    timestamp = datetime.now().strftime('%m/%d/%Y, %H:%M:%S')
    print(f"[{timestamp}] {msg}")

def get_random_delay(min_val, max_val):
    return random.randint(min_val, max_val)

def get_random_variant(variants):
    return random.choice(variants)

# -----------------------------------
# Discord HTTP API Functions
# -----------------------------------
def get_headers(include_json=False):
    headers = {
        'Authorization': TOKEN,
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
        'X-Debug-Options': 'bugReporterEnabled'
    }
    
    if include_json:
        headers['Content-Type'] = 'application/json'
    
    return headers

def initialize_session():
    try:
        log('🔐 Initializing Discord session...')
        response = session.get('https://discord.com/app', headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9'
        }, timeout=10)
        
        if response.cookies:
            global cookie_jar
            cookie_jar = dict(response.cookies)
            log('✅ Session cookies obtained')
        
        return True
    except Exception as e:
        log(f'⚠️ Session init failed: {e}')
        return False

def send_message(channel_id, content, retries=0):
    url = f'https://discord.com/api/v9/channels/{channel_id}/messages'
    
    try:
        response = session.post(
            url,
            headers=get_headers(include_json=True),
            json={'content': content},
            cookies=cookie_jar,
            timeout=10
        )
        
        if response.status_code in [200, 204]:
            log(f'✅ Message sent successfully')
            try:
                return response.json() if response.text else {}
            except:
                return {}
                
        elif response.status_code == 429:
            data = response.json()
            retry_after = data.get('retry_after', 60)
            log(f'⚠️ Rate limited. Retrying after {retry_after} seconds...')
            time.sleep(retry_after)
            return send_message(channel_id, content, retries)
            
        elif response.status_code in [401, 403]:
            log(f'🚫 Authentication failed! Status: {response.status_code}')
            log(f'Response: {response.text[:300]}')
            raise Exception(f'Auth failed: {response.status_code} - Check token validity')
            
        else:
            log(f'❌ HTTP {response.status_code}: {response.text[:200]}')
            raise Exception(f'HTTP {response.status_code}')
            
    except Exception as error:
        if retries < MAX_RETRIES:
            log(f'⚠️ Send failed (attempt {retries + 1}/{MAX_RETRIES}): {error}')
            log(f'🔄 Retrying in {RETRY_DELAY} seconds...')
            time.sleep(RETRY_DELAY)
            return send_message(channel_id, content, retries + 1)
        else:
            log(f'❌ Failed to send message after {MAX_RETRIES} attempts')
            message_counts['errors'] += 1
            raise error

def get_channel_messages(channel_id, limit=10):
    url = f'https://discord.com/api/v9/channels/{channel_id}/messages?limit={limit}'
    
    try:
        response = session.get(
            url,
            headers=get_headers(),
            cookies=cookie_jar,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f'HTTP {response.status_code}')
            
    except Exception as e:
        log(f'⚠️ Failed to fetch messages: {e}')
        return []

def click_button(message_id, channel_id, custom_id, guild_id, retries=0):
    url = 'https://discord.com/api/v9/interactions'
    
    # Simulate human delay
    human_delay = get_random_delay(300, 1200) / 1000.0
    time.sleep(human_delay)
    
    try:
        payload = {
            'type': 3,  # Component interaction
            'guild_id': guild_id,
            'channel_id': channel_id,
            'message_id': message_id,
            'data': {
                'component_type': 2,  # Button
                'custom_id': custom_id
            }
        }
        
        response = session.post(
            url,
            headers=get_headers(include_json=True),
            json=payload,
            cookies=cookie_jar,
            timeout=10
        )
        
        if response.status_code in [204, 200]:
            return True
            
        elif response.status_code == 429:
            data = response.json()
            retry_after = data.get('retry_after', 60)
            log(f'⚠️ Rate limited on button click. Retrying after {retry_after} seconds...')
            time.sleep(retry_after)
            return click_button(message_id, channel_id, custom_id, guild_id, retries)
            
        else:
            raise Exception(f'HTTP {response.status_code}')
            
    except Exception as error:
        if retries < MAX_RETRIES:
            log(f'⚠️ Button click failed (attempt {retries + 1}/{MAX_RETRIES}): {error}')
            time.sleep(RETRY_DELAY)
            return click_button(message_id, channel_id, custom_id, guild_id, retries + 1)
        else:
            log(f'❌ Failed to click button after {MAX_RETRIES} attempts')
            return False

# -----------------------------------
# Bot A Handler (SD Command)
# -----------------------------------
def check_bot_a_drops(our_message_id):
    try:
        messages = get_channel_messages(BOT_A_CHANNEL_ID, 5)
        
        for message in messages:
            if message['author']['id'] != BOT_A_ID:
                continue
            if 'dropping' not in message['content'].lower():
                continue
            
            # Check if it's a reply to our message
            if message.get('referenced_message', {}).get('id') != our_message_id:
                continue
            
            log('[BOT-A] 🎴 Drop detected!')
            
            if not message.get('components') or len(message['components']) == 0:
                log('[BOT-A] ❌ No buttons found')
                continue
            
            buttons = message['components'][0]['components']
            
            # Parse button values
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
            
            button_data = []
            for i, button in enumerate(buttons):
                value = parse_value(button.get('label', ''))
                button_data.append({
                    'index': i,
                    'value': value,
                    'custom_id': button.get('custom_id')
                })
                log(f'[BOT-A]    Button {i}: Value = {value}')
            
            # Find max value button
            max_button = max(button_data, key=lambda x: x['value'])
            
            log(f'[BOT-A] ✅ Selecting button {max_button["index"]} with value {max_button["value"]}')
            
            success = click_button(message['id'], BOT_A_CHANNEL_ID, max_button['custom_id'], BOT_A_GUILD_ID)
            
            if success:
                log('[BOT-A] 🎉 Button clicked successfully!')
            
            break
            
    except Exception as e:
        log(f'[BOT-A] ⚠️ Error checking drops: {e}')

def bot_a_loop():
    cycle = 0
    
    while True:
        try:
            cycle += 1
            command = get_random_variant(CMD_A_VARIANTS)
            
            log(f'[BOT-A] 📤 Sending command: {command}')
            sent_message = send_message(BOT_A_CHANNEL_ID, command)
            message_counts['botA'] += 1
            
            log(f'[BOT-A] ✅ Sent successfully (cycle {cycle})')
            
            # Wait for response and check for drops
            time.sleep(3)
            if sent_message and 'id' in sent_message:
                check_bot_a_drops(sent_message['id'])
            
        except Exception as error:
            log(f'[BOT-A] ❌ Error in cycle {cycle}: {error}')
        
        wait_time = get_random_delay(CMD_A_MIN_DELAY, CMD_A_MAX_DELAY)
        variance = int(wait_time * 0.1)
        final_wait = wait_time + get_random_delay(-variance, variance)
        
        log(f'[BOT-A] ⏰ Next command in {final_wait/60:.1f} minutes\n')
        time.sleep(final_wait)

# -----------------------------------
# Bot B Handler (NS Command)
# -----------------------------------
def check_bot_b_drops(our_message_id):
    try:
        messages = get_channel_messages(BOT_B_CHANNEL_ID, 10)
        
        button_message = None
        stats_message = None
        
        # Find the button message and stats message
        for message in messages:
            if message['author']['id'] != BOT_B_ID:
                continue
            
            if message.get('components') and len(message['components']) > 0:
                button_message = message
            
            # Find stats message (references button message, has WL values)
            if message.get('reference') and '¦' in message['content']:
                if button_message and message['reference'].get('message_id') == button_message['id']:
                    stats_message = message
                    break
        
        if not button_message or not stats_message:
            return
        
        log('[BOT-B] 🎴 Drop detected!')
        log('[BOT-B] 📊 Stats message found!')
        
        # Parse card values from stats message
        lines = stats_message['content'].split('\n')
        card_values = []
        
        for line in lines:
            import re
            match = re.search(r'`\s*(\d+)`\s*<:nwl_s:', line)
            if match:
                card_values.append(int(match.group(1)))
        
        log(f'[BOT-B]    Card values: {card_values}')
        
        if len(card_values) == 0:
            log('[BOT-B] ❌ No card values found')
            return
        
        max_value = max(card_values)
        highest_index = card_values.index(max_value)
        
        log(f'[BOT-B] ✅ Highest value: {max_value} at position {highest_index + 1}')
        
        buttons = button_message['components'][0]['components']
        target_button = buttons[highest_index]
        
        success = click_button(button_message['id'], BOT_B_CHANNEL_ID, target_button['custom_id'], BOT_B_GUILD_ID)
        
        if success:
            log(f'[BOT-B] 🎉 Clicked button {highest_index + 1} successfully!')
        
    except Exception as e:
        log(f'[BOT-B] ⚠️ Error checking drops: {e}')

def bot_b_loop():
    cycle = 0
    
    while True:
        try:
            cycle += 1
            command = get_random_variant(CMD_B_VARIANTS)
            
            log(f'[BOT-B] 📤 Sending command: {command}')
            sent_message = send_message(BOT_B_CHANNEL_ID, command)
            message_counts['botB'] += 1
            
            log(f'[BOT-B] ✅ Sent successfully (cycle {cycle})')
            
            # Wait for response and check for drops
            time.sleep(3)
            if sent_message and 'id' in sent_message:
                check_bot_b_drops(sent_message['id'])
            
        except Exception as error:
            log(f'[BOT-B] ❌ Error in cycle {cycle}: {error}')
        
        wait_time = get_random_delay(CMD_B_MIN_DELAY, CMD_B_MAX_DELAY)
        variance = int(wait_time * 0.1)
        final_wait = wait_time + get_random_delay(-variance, variance)
        
        log(f'[BOT-B] ⏰ Next command in {final_wait/60:.1f} minutes\n')
        time.sleep(final_wait)

# -----------------------------------
# HTTP Keep-Alive Server
# -----------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    uptime_seconds = time.time() - start_time
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    
    return jsonify({
        'status': 'alive',
        'uptime': f'{hours}h {minutes}m',
        'messages_sent': message_counts,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/ping')
def ping():
    return 'pong'

@app.route('/stats')
def stats():
    return jsonify(message_counts)

def run_flask():
    from werkzeug.serving import make_server
    port = int(os.environ.get('PORT', 10000))
    log(f'🌐 HTTP server starting on port {port}')
    
    server = make_server('0.0.0.0', port, app, threaded=True)
    log(f'✅ Flask server ready')
    log(f'🔗 Keep-alive URL: http://localhost:{port}/ping\n')
    server.serve_forever()

# -----------------------------------
# Main Execution
# -----------------------------------
if __name__ == '__main__':
    start_time = time.time()
    
    log('🚀 Starting Discord Bot (HTTP API Method)')
    log('✅ Using stable HTTP-based approach')
    
    # Initialize session
    initialize_session()
    
    log('👀 Monitoring for drops...\n')
    
    # Random initial delays
    initial_delay_a = get_random_delay(0, 30)
    initial_delay_b = get_random_delay(0, 30)
    
    log(f'[BOT-A] ⏳ Starting in {initial_delay_a} seconds...')
    log(f'[BOT-B] ⏳ Starting in {initial_delay_b} seconds...\n')
    
    # Start bot threads FIRST (before Flask)
    # Start Bot A loop with proper thread function
    def start_bot_a():
        log('[BOT-A] 🔵 Thread started, waiting for initial delay...')
        time.sleep(initial_delay_a)
        log('[BOT-A] 🟢 Initial delay complete, starting main loop...')
        bot_a_loop()
    
    # Start Bot B loop with proper thread function
    def start_bot_b():
        log('[BOT-B] 🔵 Thread started, waiting for initial delay...')
        time.sleep(initial_delay_b)
        log('[BOT-B] 🟢 Initial delay complete, starting main loop...')
        bot_b_loop()
    
    bot_a_thread = threading.Thread(target=start_bot_a, daemon=False)  # Changed to non-daemon
    bot_a_thread.start()
    log(f'✅ Bot A thread started: {bot_a_thread.is_alive()}')
    
    bot_b_thread = threading.Thread(target=start_bot_b, daemon=False)  # Changed to non-daemon
    bot_b_thread.start()
    log(f'✅ Bot B thread started: {bot_b_thread.is_alive()}\n')
    
    time.sleep(1)  # Give threads a moment to start
    
    # Start Flask server last (in main thread, not daemon)
    log('🌐 Starting Flask server in main thread...')
    run_flask()
