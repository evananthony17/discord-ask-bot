import re
import discord
from datetime import datetime, timedelta, timezone
from config import FINAL_ANSWER_CHANNEL, ANSWERING_CHANNEL, RECENT_MENTION_HOURS, RECENT_MENTION_LIMIT
from utils import normalize_name
from logging_system import log_error

# -------- RECENT MENTIONS CHECKING --------

async def check_recent_player_mentions(guild, players_to_check):
    """Check if any of the players were mentioned in the last X hours in bot messages only"""
    print(f"RECENT MENTION CHECK: Checking {len(players_to_check)} players")
    for p in players_to_check:
        print(f"RECENT MENTION CHECK: Looking for '{p['name']}' ({p['team']})")
    
    time_threshold = datetime.now(timezone.utc) - timedelta(hours=RECENT_MENTION_HOURS)
    print(f"RECENT MENTION CHECK: Time threshold: {time_threshold}")
    recent_mentions = []
    
    # Get both channels
    final_channel = discord.utils.get(guild.text_channels, name=FINAL_ANSWER_CHANNEL)
    answering_channel = discord.utils.get(guild.text_channels, name=ANSWERING_CHANNEL)
    
    print(f"RECENT MENTION CHECK: Final channel: {final_channel}")
    print(f"RECENT MENTION CHECK: Answering channel: {answering_channel}")
    
    for player in players_to_check:
        player_name_normalized = normalize_name(player['name'])
        player_uuid = player['uuid'].lower()
        
        print(f"RECENT MENTION CHECK: Checking player '{player['name']}' (normalized: '{player_name_normalized}', uuid: {player_uuid[:8]}...)")
        
        # Track where the player was found
        found_in_answering = False
        found_in_final = False
        
        # Check question reposting channel (answering channel) for BOT messages only
        if answering_channel:
            try:
                message_count = 0
                async for message in answering_channel.history(after=time_threshold, limit=RECENT_MENTION_LIMIT):
                    message_count += 1
                    # Only check messages from the bot itself
                    if message.author == guild.me:  # guild.me is the bot
                        message_normalized = normalize_name(message.content)
                        if (re.search(rf"\b{re.escape(player_name_normalized)}\b", message_normalized) or 
                            player_uuid in message_normalized):
                            print(f"RECENT MENTION CHECK: Found {player['name']} in bot message in answering channel")
                            print(f"RECENT MENTION CHECK: Message content snippet: '{message.content[:100]}...'")
                            found_in_answering = True
                            break
                print(f"RECENT MENTION CHECK: Checked {message_count} messages in answering channel")
            except Exception as e:
                log_error(f"RECENT MENTION CHECK: Error checking answering channel: {e}")
        
        # Check final answer channel for BOT messages only
        if final_channel:
            try:
                message_count = 0
                async for message in final_channel.history(after=time_threshold, limit=RECENT_MENTION_LIMIT):
                    message_count += 1
                    # Only check messages from the bot itself
                    if message.author == guild.me:  # guild.me is the bot
                        message_normalized = normalize_name(message.content)
                        if (re.search(rf"\b{re.escape(player_name_normalized)}\b", message_normalized) or 
                            player_uuid in message_normalized):
                            print(f"RECENT MENTION CHECK: Found {player['name']} in bot message in final channel")
                            print(f"RECENT MENTION CHECK: Message content snippet: '{message.content[:100]}...'")
                            found_in_final = True
                            break
                print(f"RECENT MENTION CHECK: Checked {message_count} messages in final channel")
            except Exception as e:
                log_error(f"RECENT MENTION CHECK: Error checking final channel: {e}")
        
        # Determine status based on where the player was found
        status = None
        if found_in_answering and found_in_final:
            status = "answered"  # Asked and answered
            print(f"RECENT MENTION CHECK: {player['name']} found in both channels - status: answered")
        elif found_in_answering and not found_in_final:
            status = "pending"   # Asked but not answered
            print(f"RECENT MENTION CHECK: {player['name']} found only in answering channel - status: pending")
        elif not found_in_answering and found_in_final:
            status = "answered"  # Edge case: only in final (shouldn't happen normally)
            print(f"RECENT MENTION CHECK: {player['name']} found only in final channel - status: answered (edge case)")
        else:
            print(f"RECENT MENTION CHECK: {player['name']} NOT FOUND in either channel")
        # If not found in either channel, status remains None (no recent mention)
        
        # Add to results if found (avoid duplicates by name+team)
        if status:
            # Check if we already have this exact player (name + team) - NORMALIZED
            already_added = False
            for existing in recent_mentions:
                if (normalize_name(existing["player"]["name"]) == normalize_name(player["name"]) and 
                    normalize_name(existing["player"]["team"]) == normalize_name(player["team"])):
                    already_added = True
                    print(f"RECENT MENTION CHECK: Skipping duplicate recent mention for {player['name']} ({player['team']})")
                    break
            
            if not already_added:
                recent_mentions.append({
                    "player": player,
                    "status": status
                })
                print(f"RECENT MENTION CHECK: Added recent mention: {player['name']} ({player['team']}) - {status}")
    
    print(f"RECENT MENTION CHECK: Final result: {len(recent_mentions)} recent mentions found")
    return recent_mentions

# -------- FALLBACK RECENT MENTIONS CHECK --------

async def check_fallback_recent_mentions(guild, potential_player_words):
    """Fallback check for recent mentions using potential player words"""
    time_threshold = datetime.now(timezone.utc) - timedelta(hours=RECENT_MENTION_HOURS)
    
    answering_channel = discord.utils.get(guild.text_channels, name=ANSWERING_CHANNEL)
    final_channel = discord.utils.get(guild.text_channels, name=FINAL_ANSWER_CHANNEL)
    
    for word in potential_player_words:
        # Check answering channel
        if answering_channel:
            try:
                async for message in answering_channel.history(after=time_threshold, limit=RECENT_MENTION_LIMIT):
                    if message.author == guild.me:
                        message_normalized = normalize_name(message.content)
                        if word in message_normalized:
                            print(f"FALLBACK: Found '{word}' in recent bot message in answering channel")
                            return True
            except Exception as e:
                log_error(f"FALLBACK: Error checking answering channel: {e}")
        
        # Check final channel
        if final_channel:
            try:
                async for message in final_channel.history(after=time_threshold, limit=RECENT_MENTION_LIMIT):
                    if message.author == guild.me:
                        message_normalized = normalize_name(message.content)
                        if word in message_normalized:
                            print(f"FALLBACK: Found '{word}' in recent bot message in final channel")
                            return True
            except Exception as e:
                log_error(f"FALLBACK: Error checking final channel: {e}")
    
    return False