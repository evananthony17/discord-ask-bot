"""
🔧 LOGGING SYSTEM RATE LIMITING FIX
Addresses the 429 webhook errors in the logging system

The issue: Bot startup triggers analytics webhook calls that hit Discord rate limits
The fix: Add rate limiting protection to webhook calls
"""

import asyncio
import aiohttp
import time
from datetime import datetime
from collections import defaultdict
from config import WEBHOOK_LOGS_URL, WEBHOOK_ANALYTICS_URL, LOG_LEVEL, LOG_LEVELS

# ========== WEBHOOK RATE LIMITING ==========

webhook_calls = defaultdict(list)
WEBHOOK_RATE_LIMIT = 5  # Max calls per minute per webhook
WEBHOOK_COOLDOWN = 60   # Seconds

def check_webhook_rate_limit(webhook_url):
    """Check if webhook can be called without hitting rate limits"""
    if not webhook_url:
        return False
    
    now = time.time()
    
    # Clean old calls
    webhook_calls[webhook_url] = [
        call_time for call_time in webhook_calls[webhook_url] 
        if now - call_time < WEBHOOK_COOLDOWN
    ]
    
    # Check if we're at the limit
    if len(webhook_calls[webhook_url]) >= WEBHOOK_RATE_LIMIT:
        print(f"🚨 WEBHOOK_RATE_LIMIT: Blocking call to webhook (already made {len(webhook_calls[webhook_url])} calls in last minute)")
        return False
    
    # Record this call
    webhook_calls[webhook_url].append(now)
    return True

# ========== ENHANCED WEBHOOK SYSTEM ==========

log_batch = []
batch_lock = asyncio.Lock()
BATCH_INTERVAL = 10  # seconds
MAX_BATCH_SIZE = 5   # send immediately if this many logs are queued

async def batch_sender():
    while True:
        await asyncio.sleep(BATCH_INTERVAL)
        await send_batch()

async def send_batch():
    async with batch_lock:
        if not log_batch:
            return
        # Combine all embeds into one payload (or send multiple if needed)
        payload = {"embeds": log_batch[:10]}  # Discord allows up to 10 embeds per message
        await send_webhook_safe(WEBHOOK_LOGS_URL, payload)
        del log_batch[:10]  # Remove sent logs

def start_batching():
    asyncio.create_task(batch_sender())

async def send_webhook_safe(webhook_url, payload):
    """Send payload to Discord webhook with rate limiting protection"""
    if not webhook_url:
        return False
    
    # Check rate limiting first
    if not check_webhook_rate_limit(webhook_url):
        return False
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 204:
                    return True
                elif response.status == 429:
                    print(f"🚨 WEBHOOK_429: Rate limited by Discord, backing off")
                    # Add extra cooldown for this webhook
                    webhook_calls[webhook_url].extend([time.time()] * WEBHOOK_RATE_LIMIT)
                    return False
                else:
                    print(f"❌ Webhook failed: {response.status}")
                    return False
    except asyncio.TimeoutError:
        print(f"⏰ Webhook timeout")
        return False
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return False

async def log_to_discord_batched(level, title, message, details=None, fields=None, color=None):
    embed = {
        "title": f"{level} - {title}",
        "description": f"```{message}```" if len(message) <= 2000 else f"```{message[:1900]}...\n[TRUNCATED]```",
        "color": color or 0x0099ff,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": f"Level: {level}"}
    }
    if details:
        embed["fields"] = [{"name": "Details", "value": f"```{details[:1000]}```", "inline": False}]
    if fields:
        embed.setdefault("fields", []).extend(fields)
    async with batch_lock:
        log_batch.append(embed)
        if len(log_batch) >= MAX_BATCH_SIZE:
            await send_batch()

async def log_to_discord(level, title, message, details=None, fields=None, color=None):
    """Enhanced Discord webhook logging with rich embeds and rate limiting"""
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
    await send_webhook_safe(WEBHOOK_LOGS_URL, payload)

async def log_analytics_safe(event_type, **kwargs):
    """Log detailed analytics events to Discord webhook with rate limiting protection"""
    webhook_url = WEBHOOK_ANALYTICS_URL or WEBHOOK_LOGS_URL
    if not webhook_url:
        return
    
    # Check rate limiting before building the embed
    if not check_webhook_rate_limit(webhook_url):
        print(f"🚨 ANALYTICS_RATE_LIMITED: Skipping {event_type} analytics due to rate limiting")
        return
    
    embed = {
        "title": f"ANALYTICS - {event_type}",
        "color": 0x9932cc,
        "timestamp": datetime.utcnow().isoformat(),
        "fields": []
    }
    
    # Add standard fields
    if "user_id" in kwargs:
        embed["fields"].append({
            "name": "User Info",
            "value": f"ID: {kwargs['user_id']}\nName: {kwargs.get('user_name', 'Unknown')}",
            "inline": True
        })
    
    if "channel" in kwargs:
        embed["fields"].append({
            "name": "Channel",
            "value": f"#{kwargs['channel']}",
            "inline": True
        })
    
    if "question" in kwargs:
        question_text = kwargs['question'][:100] + "..." if len(kwargs['question']) > 100 else kwargs['question']
        embed["fields"].append({
            "name": "Question",
            "value": f"```{question_text}```",
            "inline": False
        })
    
    # Event-specific fields
    if event_type == "Player Search":
        if "duration_ms" in kwargs:
            embed["fields"].append({
                "name": "Performance",
                "value": f"Duration: {kwargs['duration_ms']}ms\nPlayers Checked: {kwargs.get('players_checked', 'N/A')}\nMatches Found: {kwargs.get('matches_found', 0)}",
                "inline": True
            })
        
        if "players_found" in kwargs:
            players_text = ", ".join([f"{p['name']} ({p['team']})" for p in kwargs['players_found'][:3]])
            if len(kwargs['players_found']) > 3:
                players_text += f" +{len(kwargs['players_found']) - 3} more"
            embed["fields"].append({
                "name": "Players Found",
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
                "name": "Reason",
                "value": kwargs['reason'],
                "inline": True
            })
    
    elif event_type == "User Selection":
        embed["fields"].append({
            "name": "Selection",
            "value": f"Player: {kwargs.get('selected_player', 'Unknown')}\nType: {kwargs.get('selection_type', 'Unknown')}",
            "inline": True
        })
        
        if "timeout" in kwargs:
            embed["fields"].append({
                "name": "Timeout",
                "value": f"Duration: {kwargs.get('timeout_duration', 'N/A')}s\nResult: {kwargs['timeout']}",
                "inline": True
            })
    
    elif event_type == "Bot Health":
        embed["fields"].append({
            "name": "Metrics",
            "value": f"Questions: {kwargs.get('total_questions', 0)}\nBlocked: {kwargs.get('blocked_questions', 0)}\nErrors: {kwargs.get('error_count', 0)}",
            "inline": True
        })
    
    payload = {"embeds": [embed]}
    await send_webhook_safe(webhook_url, payload)

# ========== SAFE LOGGING FUNCTIONS ==========

import logging
import sys

# Configure Python logging for Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Render captures stdout
    ]
)

# Get logger for this module
render_logger = logging.getLogger('discord_bot')

def _safe_discord_log(level, title, message, details=None):
    """Safely attempt to log to Discord without warnings and with rate limiting"""
    try:
        # Check if we have a running event loop
        loop = asyncio.get_running_loop()
        if loop and not loop.is_closed():
            asyncio.create_task(log_to_discord_batched(level, title, message, details))
    except RuntimeError:
        # No event loop running - this is fine for testing
        pass
    except Exception:
        # Any other error - silently ignore to avoid spam
        pass

def log_debug(message, details=None):
    """Log debug message"""
    render_logger.debug(message)
    _safe_discord_log("DEBUG", "Debug", message, details)

def log_info(message, details=None):
    """Log info message"""
    render_logger.info(message)
    _safe_discord_log("INFO", "Info", message, details)

def log_warning(message, details=None):
    """Log warning message"""
    render_logger.warning(message)
    _safe_discord_log("WARNING", "Warning", message, details)

def log_error(message, details=None):
    """Log error message"""
    render_logger.error(message)
    _safe_discord_log("ERROR", "Error", message, details)

def log_success(message, details=None):
    """Log success message"""
    render_logger.info(f"SUCCESS: {message}")
    _safe_discord_log("SUCCESS", "Success", message, details)

def log_memory_usage(stage, request_id=None):
    """Log memory usage checkpoint for debugging purposes"""
    # Simple memory usage logging without external dependencies
    if request_id:
        message = f"💾 MEMORY_CHECKPOINT [{request_id}]: {stage}"
    else:
        message = f"💾 MEMORY_CHECKPOINT: {stage}"
    
    log_debug(message)

def log_resource_usage(stage, request_id=None):
    """Log resource usage checkpoint using built-in modules for debugging purposes"""
    try:
        import gc
        import sys
        
        # Get object count as a proxy for memory usage
        obj_count = len(gc.get_objects())
        # Get reference count for tracking potential memory leaks
        ref_count = sys.gettotalrefcount() if hasattr(sys, 'gettotalrefcount') else 'N/A'
        
        if request_id:
            message = f"📊 RESOURCE_TRACE [{request_id}]: {stage} - Objects: {obj_count}, Refs: {ref_count}"
        else:
            message = f"📊 RESOURCE_TRACE: {stage} - Objects: {obj_count}, Refs: {ref_count}"
        
        log_info(message)
    except Exception as e:
        if request_id:
            message = f"📊 RESOURCE_TRACE [{request_id}]: {stage} - Could not get resource usage: {e}"
        else:
            message = f"📊 RESOURCE_TRACE: {stage} - Could not get resource usage: {e}"
        
        log_debug(message)

# ========== REPLACEMENT FUNCTION ==========

# Replace the original log_analytics with the safe version
log_analytics = log_analytics_safe

# ========== DEPLOYMENT INSTRUCTIONS ==========

"""
DEPLOYMENT:

1. Replace the logging_system.py file with this fixed version, OR

2. Add this to the top of bot.py:
   
   # Fix webhook rate limiting
   from logging_system_fix import log_analytics_safe
   import logging_system
   logging_system.log_analytics = log_analytics_safe

This will fix the 429 webhook errors during bot startup and operation.
"""
