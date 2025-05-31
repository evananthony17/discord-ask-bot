import asyncio
import aiohttp
from datetime import datetime
from config import WEBHOOK_LOGS_URL, WEBHOOK_ANALYTICS_URL, LOG_LEVEL, LOG_LEVELS

# -------- ENHANCED WEBHOOK LOGGING SYSTEM --------

async def send_webhook(webhook_url, payload):
    """Send payload to Discord webhook with error handling"""
    if not webhook_url:
        return False
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                if response.status == 204:
                    return True
                else:
                    print(f"❌ Webhook failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return False

async def log_to_discord(level, title, message, details=None, fields=None, color=None):
    """Enhanced Discord webhook logging with rich embeds"""
    if not WEBHOOK_LOGS_URL:
        return
    
    current_level = LOG_LEVELS.get(LOG_LEVEL, 1)
    msg_level = LOG_LEVELS.get(level, 1)
    
    if msg_level < current_level:
        return
    
    colors = {
        "DEBUG": 0x808080,    # Gray
        "INFO": 0x0099ff,     # Blue  
        "WARNING": 0xff9900,  # Orange
        "ERROR": 0xff0000,    # Red
        "SUCCESS": 0x00ff00,  # Green
        "ANALYTICS": 0x9932cc # Purple
    }
    
    embed = {
        "title": f"{level} - {title}",
        "description": f"```{message}```" if len(message) <= 2000 else f"```{message[:1900]}...\n[TRUNCATED]```",
        "color": color or colors.get(level, 0x0099ff),
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": f"Level: {level}"}
    }
    
    if details:
        embed["fields"] = [{"name": "Details", "value": f"```{details[:1000]}```", "inline": False}]
    
    if fields:
        embed.setdefault("fields", []).extend(fields)
    
    payload = {"embeds": [embed]}
    await send_webhook(WEBHOOK_LOGS_URL, payload)

async def log_analytics(event_type, **kwargs):
    """Log detailed analytics events to Discord webhook"""
    webhook_url = WEBHOOK_ANALYTICS_URL or WEBHOOK_LOGS_URL
    if not webhook_url:
        return
    
    embed = {
        "title": f"📊 ANALYTICS - {event_type}",
        "color": 0x9932cc,
        "timestamp": datetime.utcnow().isoformat(),
        "fields": []
    }
    
    # Add standard fields
    if "user_id" in kwargs:
        embed["fields"].append({
            "name": "👤 User Info",
            "value": f"ID: {kwargs['user_id']}\nName: {kwargs.get('user_name', 'Unknown')}",
            "inline": True
        })
    
    if "channel" in kwargs:
        embed["fields"].append({
            "name": "📍 Channel",
            "value": f"#{kwargs['channel']}",
            "inline": True
        })
    
    if "question" in kwargs:
        question_text = kwargs['question'][:100] + "..." if len(kwargs['question']) > 100 else kwargs['question']
        embed["fields"].append({
            "name": "❓ Question",
            "value": f"```{question_text}```",
            "inline": False
        })
    
    # Event-specific fields
    if event_type == "Player Search":
        if "duration_ms" in kwargs:
            embed["fields"].append({
                "name": "⚡ Performance",
                "value": f"Duration: {kwargs['duration_ms']}ms\nPlayers Checked: {kwargs.get('players_checked', 'N/A')}\nMatches Found: {kwargs.get('matches_found', 0)}",
                "inline": True
            })
        
        if "players_found" in kwargs:
            players_text = ", ".join([f"{p['name']} ({p['team']})" for p in kwargs['players_found'][:3]])
            if len(kwargs['players_found']) > 3:
                players_text += f" +{len(kwargs['players_found']) - 3} more"
            embed["fields"].append({
                "name": "🎯 Players Found",
                "value": f"```{players_text}```",
                "inline": False
            })
    
    elif event_type == "Question Processed":
        status_emoji = {"approved": "✅", "blocked": "🚫", "disambiguation": "🤔"}.get(kwargs.get('status'), "❓")
        embed["fields"].append({
            "name": f"{status_emoji} Status",
            "value": kwargs.get('status', 'Unknown').title(),
            "inline": True
        })
        
        if "reason" in kwargs:
            embed["fields"].append({
                "name": "📝 Reason",
                "value": kwargs['reason'],
                "inline": True
            })
    
    elif event_type == "User Selection":
        embed["fields"].append({
            "name": "🎯 Selection",
            "value": f"Player: {kwargs.get('selected_player', 'Unknown')}\nType: {kwargs.get('selection_type', 'Unknown')}",
            "inline": True
        })
        
        if "timeout" in kwargs:
            embed["fields"].append({
                "name": "⏰ Timeout",
                "value": f"Duration: {kwargs.get('timeout_duration', 'N/A')}s\nResult: {kwargs['timeout']}",
                "inline": True
            })
    
    elif event_type == "Bot Health":
        embed["fields"].append({
            "name": "📈 Metrics",
            "value": f"Questions: {kwargs.get('total_questions', 0)}\nBlocked: {kwargs.get('blocked_questions', 0)}\nErrors: {kwargs.get('error_count', 0)}",
            "inline": True
        })
    
    payload = {"embeds": [embed]}
    await send_webhook(webhook_url, payload)

# -------- SIMPLIFIED LOGGING FUNCTIONS --------

def log_debug(message, details=None):
    """Log debug message"""
    print(f"🔍 DEBUG: {message}")
    asyncio.create_task(log_to_discord("DEBUG", "Debug", message, details))

def log_info(message, details=None):
    """Log info message"""
    print(f"ℹ️ INFO: {message}")
    asyncio.create_task(log_to_discord("INFO", "Info", message, details))

def log_warning(message, details=None):
    """Log warning message"""
    print(f"⚠️ WARNING: {message}")
    asyncio.create_task(log_to_discord("WARNING", "Warning", message, details))

def log_error(message, details=None):
    """Log error message"""
    print(f"❌ ERROR: {message}")
    asyncio.create_task(log_to_discord("ERROR", "Error", message, details))

def log_success(message, details=None):
    """Log success message"""
    print(f"✅ SUCCESS: {message}")
    asyncio.create_task(log_to_discord("SUCCESS", "Success", message, details))