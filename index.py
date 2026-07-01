import requests
import time
import random
import os
import threading
import uuid
import re
from datetime import datetime
from flask import Flask, jsonify, request

# =============================================
# CONFIGURATION
# =============================================

# Get token from environment variable
TOKEN = os.environ.get("AUTH_TOKEN", "").strip()

# Nai Bot IDs
NAI_BOT_ID = '1312830013573169252'
GUILD_ID = os.environ.get("DISCORD_GUILD_ID", "1416026295090938008").strip()

# Channel where Nai bot operates
CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID", "1416026296185786399").strip()

# Messages to send (randomized case to avoid detection)
TRIGGER_MESSAGES = ['ns', 'nS', 'Ns', 'NS']

# =============================================
# DELAY CONFIGURATION
# =============================================

# Random delay between cycles: 660-1080 seconds (11-18 minutes)
DELAY_MIN = 660   # 11 minutes
DELAY_MAX = 1080  # 18 minutes

# Response wait time after sending message (check after 4s, wait up to 15s)
RESPONSE_WAIT_MIN = 4   # Minimum 4 seconds
RESPONSE_WAIT_MAX = 15  # Maximum 15 seconds

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 10

# =============================================
# FLASK SETUP
# =============================================

app = Flask(__name__)

# =============================================
# STATS TRACKING
# =============================================

message_counts = {
    'sd': 0,              # Total messages sent
    'clicks': 0,          # Successful button clicks
    'click_fails': 0,     # Failed button clicks
    'cards_parsed': 0,    # Times card data was successfully parsed
    'low_value_hits': 0,  # Times condition 1 triggered (value <= 100)
    'high_count_hits': 0  # Times condition 2 triggered (all values > 100)
}

# =============================================
# HELPER: Get Session
# =============================================

def get_session():
    """
    Create and return a requests Session with proper headers.
    This ensures all requests have the same headers and cookies.
    
    Returns:
        requests.Session: Configured session with authorization header
    """
    s = requests.Session()
    s.headers.update({
        'Authorization': TOKEN,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9'
    })
    return s

# =============================================
# HELPER: Logging
# =============================================

def log(msg):
    """
    Print a timestamped log message.
    
    Args:
        msg (str): Message to log
    """
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

# =============================================
# HELPER: Get Delay
# =============================================

def get_delay():
    """
    Get a random delay between DELAY_MIN and DELAY_MAX.
    
    Returns:
        int: Delay in seconds (660-1080)
    """
    delay = random.randint(DELAY_MIN, DELAY_MAX)
    log(f"⏳ Delay: {delay}s ({delay//60}m {delay%60}s)")
    return delay

# =============================================
# FUNCTION: Send Message to Discord
# =============================================

def send_message(channel_id, msg):
    """
    Send a message to a Discord channel.
    Handles rate limiting and retries.
    
    Args:
        channel_id (str): Discord channel ID
        msg (str): Message content to send
    
    Returns:
        dict: JSON response from Discord API, or None if failed
    """
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
                # Rate limited - wait and retry
                retry_after = 300
                try:
                    retry_after = int(r.headers.get('Retry-After', 300))
                except:
                    pass
                log(f"⚠️ Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
                return None
            else:
                log(f"⚠️ Send status {r.status_code}")
                
        except Exception as e:
            log(f"❌ Send error: {str(e)[:100]}")

        # Exponential backoff for retries
        if attempt < MAX_RETRIES:
            wait = RETRY_DELAY * (2 ** (attempt - 1))
            time.sleep(wait)

    return None

# =============================================
# FUNCTION: Get Messages from Channel
# =============================================

def get_messages(channel_id, limit=20):
    """
    Fetch recent messages from a Discord channel.
    
    Args:
        channel_id (str): Discord channel ID
        limit (int): Number of messages to fetch (max 100)
    
    Returns:
        list: List of message objects, or empty list if failed
    """
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit={limit}"
    session = get_session()
    headers = {"Authorization": TOKEN}
    
    try:
        # Random delay to appear human
        time.sleep(random.uniform(0.5, 1.5))
        r = session.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
        return []
    except Exception as e:
        log(f"⚠️ Fetch error: {e}")
        return []

def get_message_by_id(channel_id, message_id):
    """
    Fetch a specific message by ID.
    
    Args:
        channel_id (str): Discord channel ID
        message_id (str): Message ID to fetch
    
    Returns:
        dict: Message object, or None if failed
    """
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}"
    session = get_session()
    headers = {"Authorization": TOKEN}
    
    try:
        r = session.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        log(f"⚠️ Fetch message error: {e}")
        return None

# =============================================
# FUNCTION: Click a Button
# =============================================

def click_button(message_id, channel_id, custom_id, bot_id):
    """
    Click a button on a Discord message.
    
    Args:
        message_id (str): ID of the message containing the button
        channel_id (str): Discord channel ID
        custom_id (str): Custom ID of the button to click
        bot_id (str): ID of the bot that owns the button
    
    Returns:
        bool: True if successful, False otherwise
    """
    url = "https://discord.com/api/v9/interactions"
    session = get_session()
    
    headers = {
        "Authorization": TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    payload = {
        "type": 3,  # Message Component interaction
        "guild_id": GUILD_ID,
        "channel_id": channel_id,
        "message_id": message_id,
        "application_id": bot_id,
        "session_id": str(uuid.uuid4()),  # Random session ID
        "data": {
            "component_type": 2,  # Button
            "custom_id": custom_id
        },
        "message_flags": 0
    }
    
    try:
        # Random delay to appear human
        delay = random.uniform(1.0, 2.5)
        time.sleep(delay)
        
        r = session.post(url, headers=headers, json=payload, timeout=15)
        
        if r.status_code in [200, 204]:
            log(f"✅ Button clicked: {custom_id[:20]}...")
            return True
        else:
            log(f"❌ Click failed: {r.status_code} - {r.text[:200]}")
            
    except Exception as e:
        log(f"❌ Click error: {e}")
    
    return False

# =============================================
# FUNCTION: Parse Card Data
# =============================================

def parse_card_data(content):
    """
    Parse card data from Nai bot's data message.
    Extracts both count AND value for each card.
    
    Format: <emoji>¦ `count` <emoji> ¦ <emoji> ¦ `value` ¦ **Name** · *Source*
    
    Args:
        content (str): Message content containing card data
    
    Returns:
        list: List of card dictionaries with keys:
            - index (int): Card position (0, 1, 2)
            - emoji (str): Emoji name
            - count (int): First number (count/stock)
            - value (int): Second number (value/power)
            - name (str): Card name
            - source (str): Source game
    """
    lines = content.strip().split('\n')
    cards = []
    
    # Map emoji to card position
    emoji_map = {
        'none_1': 0,
        'ntwo_1': 1,
        'nthree_1': 2
    }
    
    for line in lines:
        if not line.strip():
            continue
        
        # Regex to extract: emoji, count, value, name, source
        match = re.search(r'<:(\w+):\d+>.*?¦\s*`\s*(\d+)\s*`\s*.*?¦\s*`\s*(\d+)\s*`\s*¦\s*\*\*([^*]+)\*\*\s*·\s*\*([^*]+)\*', line)
        
        if match:
            emoji_name = match.group(1)
            count = int(match.group(2).strip())
            value = int(match.group(3).strip())
            name = match.group(4).strip()
            source = match.group(5).strip()
            
            card_index = emoji_map.get(emoji_name, -1)
            
            cards.append({
                'index': card_index,
                'emoji': emoji_name,
                'count': count,
                'value': value,
                'name': name,
                'source': source
            })
    
    # Sort by index to ensure correct order
    cards.sort(key=lambda x: x['index'])
    return cards

# =============================================
# FUNCTION: Select Best Card
# =============================================

def select_best_card(cards):
    """
    Select the best card based on conditions:
    1. If ANY card has value <= 100 -> pick the LOWEST value
    2. If ALL cards have value > 100 -> pick the HIGHEST count
    
    Args:
        cards (list): List of card dictionaries from parse_card_data()
    
    Returns:
        dict: Selected card, or None if no cards
    """
    if not cards:
        return None
    
    # Check if ANY card has value <= 100
    has_low_value = any(card['value'] <= 100 for card in cards)
    
    if has_low_value:
        log("📊 Low value found (<=100) → Selecting LOWEST value")
        selected = min(cards, key=lambda x: x['value'])
        message_counts['low_value_hits'] += 1
        return selected
    else:
        log("📊 All values > 100 → Selecting HIGHEST count")
        selected = max(cards, key=lambda x: x['count'])
        message_counts['high_count_hits'] += 1
        return selected

# =============================================
# FUNCTION: Find Button Message
# =============================================

def find_button_message(messages):
    """
    Find the message containing buttons.
    Checks both direct messages and referenced messages.
    
    Args:
        messages (list): List of messages to search
    
    Returns:
        tuple: (message_object, is_referenced) or (None, False)
    """
    for msg in messages:
        if msg.get('author', {}).get('id') != NAI_BOT_ID:
            continue
        
        # Check if this message has buttons
        if msg.get('components'):
            return msg, False
        
        # Check if this message references another with buttons
        ref = msg.get('message_reference')
        if ref and ref.get('message_id'):
            referenced = get_message_by_id(CHANNEL_ID, ref['message_id'])
            if referenced and referenced.get('components'):
                return referenced, True
    
    return None, False

# =============================================
# FUNCTION: Get Buttons from Message
# =============================================

def get_buttons_from_message(msg):
    """
    Extract all clickable buttons from a message.
    
    Args:
        msg (dict): Message object
    
    Returns:
        list: List of button dictionaries with keys:
            - custom_id (str): Button custom ID
            - label (str): Button label
            - emoji (str): Button emoji name
    """
    buttons = []
    components = msg.get('components', [])
    
    for row in components:
        if row.get('type') == 1:  # Action Row
            for comp in row.get('components', []):
                if comp.get('type') == 2:  # Button
                    if not comp.get('disabled', False):  # Not disabled
                        buttons.append({
                            'custom_id': comp.get('custom_id'),
                            'label': comp.get('label', ''),
                            'emoji': comp.get('emoji', {}).get('name', '')
                        })
    return buttons

# =============================================
# FUNCTION: Find Latest Data Message
# =============================================

def find_latest_data_message(messages):
    """
    Find the most recent data message from Nai bot.
    Data messages contain card information with format: 
    <emoji>¦ `count` <emoji> ¦ <emoji> ¦ `value` ¦ **Name** · *Source*
    
    Args:
        messages (list): List of messages to search
    
    Returns:
        dict: Message object, or None if not found
    """
    for msg in messages:
        if msg.get('author', {}).get('id') != NAI_BOT_ID:
            continue
        
        content = msg.get('content', '')
        if content and '¦' in content and '**' in content:
            return msg
    
    return None

# =============================================
# FUNCTION: Process Bot Response
# =============================================

def process_response():
    """
    Process the bot's response after sending a message.
    1. Wait 4-15 seconds for response (check after 4s)
    2. Find button message
    3. Parse card data
    4. Select best card
    5. Click the button
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        log("🔍 Processing response...")
        
        # Wait for response (4-15 seconds)
        wait = random.uniform(RESPONSE_WAIT_MIN, RESPONSE_WAIT_MAX)
        log(f"⏳ Waiting {wait:.1f}s for response...")
        time.sleep(wait)
        
        # Get messages
        messages = get_messages(CHANNEL_ID, limit=20)
        if not messages:
            log("⚠️ No messages fetched")
            return False
        
        # Find button message
        button_msg, is_referenced = find_button_message(messages)
        if not button_msg:
            log("⚠️ No button message found (maybe cooldown)")
            return False
        
        log(f"✅ Found button message (Referenced: {is_referenced})")
        
        # Get buttons
        buttons = get_buttons_from_message(button_msg)
        if not buttons:
            log("⚠️ No buttons found")
            return False
        
        log(f"🔘 Found {len(buttons)} buttons")
        
        # Find data message
        data_msg = find_latest_data_message(messages)
        
        if not data_msg:
            log("⚠️ No data message found, clicking first button")
            target_button = buttons[0]
            card_name = "Unknown"
        else:
            # Parse card data
            cards = parse_card_data(data_msg.get('content', ''))
            
            if not cards or len(cards) < 3:
                log(f"⚠️ Only parsed {len(cards)} cards, using first button")
                target_button = buttons[0]
                card_name = "Unknown"
            else:
                # Log card data
                log("📊 Card Data:")
                for card in cards:
                    log(f"   {card['name']}: Count={card['count']}, Value={card['value']}")
                
                # Select best card
                selected_card = select_best_card(cards)
                if not selected_card:
                    target_button = buttons[0]
                    card_name = "Unknown"
                else:
                    message_counts['cards_parsed'] += 1
                    
                    # Find matching button
                    card_index = cards.index(selected_card)
                    if card_index < len(buttons):
                        target_button = buttons[card_index]
                        card_name = selected_card['name']
                        log(f"✅ Selected: {card_name} (Count={selected_card['count']}, Value={selected_card['value']})")
                    else:
                        target_button = buttons[0]
                        card_name = "Unknown"
        
        # Click the button
        log(f"🎯 Clicking button: {target_button['emoji']}")
        success = click_button(
            button_msg['id'],
            CHANNEL_ID,
            target_button['custom_id'],
            NAI_BOT_ID
        )
        
        if success:
            message_counts['clicks'] += 1
            log(f"✅ Success! Clicked {card_name}")
            return True
        else:
            message_counts['click_fails'] += 1
            return False
            
    except Exception as e:
        log(f"❌ Process error: {e}")
        message_counts['click_fails'] += 1
        return False

# =============================================
# FUNCTION: Main Loop
# =============================================

def main_loop():
    """
    Main automation loop.
    1. Send random variation of 'ns'
    2. Process response (wait 4-15s)
    3. Wait random delay (660-1080 seconds)
    4. Repeat forever
    """
    cycle = 0
    initial = random.randint(5, 15)
    log(f"🔵 Starting in {initial}s")
    time.sleep(initial)
    
    while True:
        cycle += 1
        log(f"\n{'='*60}")
        log(f"🔄 CYCLE #{cycle}")
        log(f"{'='*60}")
        
        # Get random message variation
        msg = random.choice(TRIGGER_MESSAGES)
        log(f"📤 Sending '{msg}'...")
        
        # Send message
        sent = send_message(CHANNEL_ID, msg)
        
        if sent:
            message_counts['sd'] += 1
            process_response()
        else:
            log("⚠️ Send failed, will retry next cycle")
        
        # Calculate random wait time (660-1080 seconds)
        wait = random.randint(DELAY_MIN, DELAY_MAX)
        log(f"⏳ Next cycle in {wait}s ({wait//60}m {wait%60}s)")
        time.sleep(wait)

# =============================================
# FUNCTION: Keep-Alive Service
# =============================================

def keep_alive():
    """
    Background thread that pings the Flask server every 10 minutes.
    Prevents Render from sleeping the service.
    """
    service_url = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:10000")
    
    time.sleep(60)  # Wait for server to start
    
    while True:
        try:
            time.sleep(600)  # 10 minutes
            
            response = requests.get(f"{service_url}/ping", timeout=10)
            
            if response.status_code == 200:
                log("💓 Keep-alive ping successful")
            else:
                log(f"⚠️ Keep-alive ping returned {response.status_code}")
                
        except Exception as e:
            log(f"⚠️ Keep-alive ping failed: {e}")

# =============================================
# FLASK ROUTES
# =============================================

@app.route("/ping")
def ping():
    """
    Health check endpoint.
    Returns "pong" to verify service is running.
    """
    return "pong"

@app.route("/")
def status():
    """
    Main status endpoint.
    Returns current stats and bot information.
    """
    return jsonify({
        'status': 'ok',
        'stats': message_counts,
        'bot': 'Nai Automation',
        'channel': CHANNEL_ID,
        'bot_id': NAI_BOT_ID
    })

@app.route("/stats")
def stats():
    """
    Detailed stats endpoint.
    Returns all statistics and current time.
    """
    return jsonify({
        'message_counts': message_counts,
        'uptime': datetime.now().isoformat(),
        'channel': CHANNEL_ID,
        'bot_id': NAI_BOT_ID,
        'guild_id': GUILD_ID
    })

def run_server():
    """
    Run the Flask server.
    Port is set by Render environment variable or default 10000.
    """
    port = int(os.environ.get('PORT', 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# =============================================
# MAIN - ENTRY POINT
# =============================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 NAI BOT AUTOMATION")
    print("="*70)
    print(f"📍 Channel: {CHANNEL_ID}")
    print(f"🤖 Bot ID: {NAI_BOT_ID}")
    print("="*70 + "\n")
    
    # Validate token
    if not TOKEN:
        log("❌ No token found!")
        log("   Set AUTH_TOKEN environment variable:")
        log("   render.com: Add environment variable AUTH_TOKEN")
        log("   local: export AUTH_TOKEN=your_token_here")
        exit(1)
    
    log(f"✅ Token OK ({len(TOKEN)} chars)")
    log(f"✅ Guild ID: {GUILD_ID}")
    log(f"✅ Channel ID: {CHANNEL_ID}")
    
    print("\n" + "="*70)
    print("📋 RULES:")
    print("="*70)
    print("   • Random message: ns/nS/Ns/NS")
    print("   • If ANY card has value <= 100 → Pick LOWEST value")
    print("   • If ALL cards have value > 100 → Pick HIGHEST count")
    print(f"   • Response wait: {RESPONSE_WAIT_MIN}-{RESPONSE_WAIT_MAX}s")
    print(f"   • Delay between cycles: {DELAY_MIN}-{DELAY_MAX}s ({DELAY_MIN//60}-{DELAY_MAX//60}m)")
    print("="*70 + "\n")
    
    # Start Flask server in background thread
    log("🌐 Starting Flask server...")
    threading.Thread(target=run_server, daemon=True).start()
    time.sleep(2)
    
    # Start keep-alive service
    log("💓 Starting keep-alive service...")
    threading.Thread(target=keep_alive, daemon=True).start()
    
    # Start main loop
    log("🔄 Starting main automation loop...")
    threading.Thread(target=main_loop, daemon=True).start()
    
    log("✅ Bot is running!\n")
    log("📊 Check status at: http://localhost:10000/")
    log("📊 Check stats at: http://localhost:10000/stats\n")
    
    # Keep main thread alive
    while True:
        time.sleep(300)
        log(f"💓 SD:{message_counts['sd']} ✅:{message_counts['clicks']} ❌:{message_counts['click_fails']} | "
            f"Cards:{message_counts['cards_parsed']} "
            f"Low:{message_counts['low_value_hits']} High:{message_counts['high_count_hits']}")
