import re
import discord
from datetime import datetime, timedelta, timezone
from config import FINAL_ANSWER_CHANNEL, ANSWERING_CHANNEL, RECENT_MENTION_HOURS, RECENT_MENTION_LIMIT
from utils import normalize_name
from logging_system import log_error, log_info

# -------- RECENT MENTIONS CHECKING --------

async def check_recent_player_mentions(guild, players_to_check):
    """Check if any of the players were mentioned in the last X hours in bot messages only"""
    log_info(f"RECENT MENTION CHECK: Checking {len(players_to_check)} players")
    for p in players_to_check:
        log_info(f"RECENT MENTION CHECK: Looking for '{p['name']}' ({p['team']})")
    
    time_threshold = datetime.now(timezone.utc) - timedelta(hours=RECENT_MENTION_HOURS)
    log_info(f"RECENT MENTION CHECK: Time threshold: {time_threshold}")
    recent_mentions = []
    
    # Get both channels
    final_channel = discord.utils.get(guild.text_channels, name=FINAL_ANSWER_CHANNEL)
    answering_channel = discord.utils.get(guild.text_channels, name=ANSWERING_CHANNEL)
    
    log_info(f"RECENT MENTION CHECK: Final channel: {final_channel}")
    log_info(f"RECENT MENTION CHECK: Answering channel: {answering_channel}")
    
    for player in players_to_check:
        # FIXED: Reset the flags for each player
        found_in_answering = False
        found_in_final = False
        
        player_name_normalized = normalize_name(player['name'])
        player_uuid = player['uuid'].lower()
        
        log_info(f"RECENT MENTION CHECK: Checking player '{player['name']}' (normalized: '{player_name_normalized}', uuid: {player_uuid[:8]}...)")
        
        # Check question reposting channel (answering channel) for BOT messages only
        if answering_channel:
            try:
                message_count = 0
                async for message in answering_channel.history(after=time_threshold, limit=RECENT_MENTION_LIMIT):
                    message_count += 1
                    # Only check messages from the bot itself
                    if message.author == guild.me:  # guild.me is the bot
                        message_normalized = normalize_name(message.content)
                        # Fix multiline regex pattern
                        pattern = f"\\b{re.escape(player_name_normalized)}"
                        if (re.search(pattern, message_normalized) or player_uuid in message_normalized):
                            log_info(f"RECENT MENTION CHECK: Found {player['name']} in bot message in answering channel")
                            log_info(f"RECENT MENTION CHECK: Match details - player_normalized: '{player_name_normalized}', message_snippet: '{message_normalized[:100]}...', uuid: '{player_uuid[:8]}'")
                            log_info(f"RECENT MENTION CHECK: Message content snippet: '{message.content[:100]}...'")
                            found_in_answering = True
                            log_info(f"RECENT MENTION CHECK: SETTING found_in_answering = True")
                            
                            # BYPASS WEBHOOK - Direct Discord message for debugging
                            try:
                                logs_channel = discord.utils.get(guild.text_channels, name="bernie-stock-logs")
                                if logs_channel:
                                    await logs_channel.send(f"🔧 **DEBUG**: found_in_answering = True for {player['name']}")
                            except:
                                pass  # Don't let debug messages break the bot
                            
                            break
                log_info(f"RECENT MENTION CHECK: Checked {message_count} messages in answering channel")
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
                        # Fix multiline regex pattern  
                        pattern = f"\\b{re.escape(player_name_normalized)}"
                        if (re.search(pattern, message_normalized) or player_uuid in message_normalized):
                            log_info(f"RECENT MENTION CHECK: Found {player['name']} in bot message in final channel")
                            log_info(f"RECENT MENTION CHECK: Match details - player_normalized: '{player_name_normalized}', message_snippet: '{message_normalized[:100]}...', uuid: '{player_uuid[:8]}'")
                            log_info(f"RECENT MENTION CHECK: Message content snippet: '{message.content[:100]}...'")
                            found_in_final = True
                            log_info(f"RECENT MENTION CHECK: SETTING found_in_final = True")
                            
                            # BYPASS WEBHOOK - Direct Discord message for debugging
                            try:
                                logs_channel = discord.utils.get(guild.text_channels, name="bernie-stock-logs")
                                if logs_channel:
                                    await logs_channel.send(f"🔧 **DEBUG**: found_in_final = True for {player['name']}")
                            except:
                                pass  # Don't let debug messages break the bot
                            
                            break
                log_info(f"RECENT MENTION CHECK: Checked {message_count} messages in final channel")
            except Exception as e:
                log_error(f"RECENT MENTION CHECK: Error checking final channel: {e}")
        
        # FIXED: Determine status based on where the player was found
        log_info(f"RECENT MENTION CHECK: Processing status for {player['name']} - found_in_answering: {found_in_answering}, found_in_final: {found_in_final}")
        
        # BYPASS WEBHOOK - Direct Discord message for status processing
        try:
            logs_channel = discord.utils.get(guild.text_channels, name="bernie-stock-logs")
            if logs_channel:
                await logs_channel.send(f"🔧 **DEBUG**: Processing {player['name']} - answering: {found_in_answering}, final: {found_in_final}")
        except:
            pass
        
        status = None
        if found_in_answering and found_in_final:
            status = "answered"  # Asked and answered
            log_info(f"RECENT MENTION CHECK: {player['name']} found in both channels - status: answered")
        elif found_in_answering and not found_in_final:
            status = "pending"   # Asked but not answered
            log_info(f"RECENT MENTION CHECK: {player['name']} found only in answering channel - status: pending")
        elif not found_in_answering and found_in_final:
            status = "answered"  # Edge case: only in final (shouldn't happen normally)
            log_info(f"RECENT MENTION CHECK: {player['name']} found only in final channel - status: answered (edge case)")
        else:
            log_info(f"RECENT MENTION CHECK: {player['name']} NOT FOUND in either channel")
            # status remains None - no recent mention
        
        # BYPASS WEBHOOK - Direct Discord message for status result
        try:
            logs_channel = discord.utils.get(guild.text_channels, name="bernie-stock-logs")
            if logs_channel:
                await logs_channel.send(f"🔧 **DEBUG**: {player['name']} status determined: {status}")
        except:
            pass
        
        # Add to results if found (avoid duplicates by name+team)
        if status:
            # Check if we already have this exact player (name + team) - NORMALIZED
            already_added = False
            for existing in recent_mentions:
                if (normalize_name(existing["player"]["name"]) == normalize_name(player["name"]) and 
                    normalize_name(existing["player"]["team"]) == normalize_name(player["team"])):
                    already_added = True
                    log_info(f"RECENT MENTION CHECK: Skipping duplicate recent mention for {player['name']} ({player['team']})")
                    break
            
            if not already_added:
                recent_mentions.append({
                    "player": player,
                    "status": status
                })
                log_info(f"RECENT MENTION CHECK: Added recent mention: {player['name']} ({player['team']}) - {status}")
                
                # BYPASS WEBHOOK - Direct Discord message for adding to results
                try:
                    logs_channel = discord.utils.get(guild.text_channels, name="bernie-stock-logs")
                    if logs_channel:
                        await logs_channel.send(f"🔧 **DEBUG**: ADDED to results: {player['name']} ({player['team']}) - {status}")
                except:
                    pass
    
    # BYPASS WEBHOOK - Direct Discord message for final result
    try:
        logs_channel = discord.utils.get(guild.text_channels, name="bernie-stock-logs")
        if logs_channel:
            await logs_channel.send(f"🔧 **DEBUG**: Final return - {len(recent_mentions)} mentions found")
            for mention in recent_mentions:
                await logs_channel.send(f"🔧 **DEBUG**: Returning player {mention['player']['name']} with status {mention['status']}")
    except:
        pass
    
    log_info(f"RECENT MENTION CHECK: Final result: {len(recent_mentions)} recent mentions found")
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
                            log_info(f"FALLBACK: Found '{word}' in recent bot message in answering channel")
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
                            log_info(f"FALLBACK: Found '{word}' in recent bot message in final channel")
                            return True
            except Exception as e:
                log_error(f"FALLBACK: Error checking final channel: {e}")
    
    return False