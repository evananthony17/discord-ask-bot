import re
import discord
from datetime import datetime, timedelta, timezone
from config import FINAL_ANSWER_CHANNEL, ANSWERING_CHANNEL, RECENT_MENTION_HOURS, RECENT_MENTION_LIMIT
from utils import normalize_name
from logging_system import log_error, log_info

# -------- HIERARCHICAL MATCHING FUNCTIONS --------

def clean_message_content_for_scanning(message_content, message_author_name):
    """
    Remove username from message content to prevent false positives
    when scanning for player mentions
    """
    # Normalize both for consistent matching
    content_normalized = normalize_name(message_content)
    author_normalized = normalize_name(message_author_name)
    
    # 🔧 FIXED: Add safety checks to prevent regex errors
    if not author_normalized or len(author_normalized.strip()) == 0:
        return content_normalized
    
    try:
        # Common bot message patterns that include usernames
        username_patterns = [
            f"\\*\\*{re.escape(author_normalized)}\\*\\* asked:",
            f"\\*\\*{re.escape(author_normalized)}\\*\\*:",
            f"{re.escape(author_normalized)} asked:",
            f"{re.escape(author_normalized)}:",
            # Handle potential variations
            f"\\*\\*{re.escape(author_normalized.replace(' ', ''))}\\*\\* asked:",
            f"\\*\\*{re.escape(author_normalized.replace(' ', ''))}\\*\\*:",
]
        
        # Remove username patterns from the content
        cleaned_content = content_normalized
        for pattern in username_patterns:
            try:
                cleaned_content = re.sub(pattern, "", cleaned_content, flags=re.IGNORECASE)
            except re.error as e:
                log_error(f"REGEX ERROR in username pattern: {e} - Pattern: {pattern}")
                continue
        
        # Also remove just the raw username if it appears
        if len(author_normalized) > 0:
            try:
                cleaned_content = re.sub(f"\\b{re.escape(author_normalized)}\\b", "", cleaned_content, flags=re.IGNORECASE)
            except re.error as e:
                log_error(f"REGEX ERROR in raw username removal: {e} - Username: {author_normalized}")
        
        # Clean up extra whitespace
        cleaned_content = re.sub(r'\s+', ' ', cleaned_content).strip()
        
        return cleaned_content
        
    except Exception as e:
        log_error(f"ERROR in clean_message_content_for_scanning: {e}")
        return content_normalized  # Return original if cleaning fails

def check_player_mention_hierarchical(player_name_normalized, player_uuid, message_normalized, message_content, message_author_name=None):
    """
    Hierarchical matching from most specific to least specific
    Returns: (is_match, match_type, confidence_score)
    """
    
    # 🔧 FIXED: Add error handling for username filtering
    try:
        if message_author_name:
            scanning_content = clean_message_content_for_scanning(message_content, message_author_name)
            scanning_normalized = normalize_name(scanning_content)
            log_info(f"🔧 USERNAME FILTER: Original: '{message_normalized[:100]}...'")
            log_info(f"🔧 USERNAME FILTER: Cleaned: '{scanning_normalized[:100]}...'")
            log_info(f"🔧 USERNAME FILTER: Removed username: '{normalize_name(message_author_name)}'")
        else:
            scanning_normalized = message_normalized
    except Exception as e:
        log_error(f"ERROR in username filtering: {e}")
        scanning_normalized = message_normalized
    
    try:
        # LEVEL 1: EXACT full name match (highest confidence = 1.0)
        exact_pattern = f"\\b{re.escape(player_name_normalized)}\\b"
        if re.search(exact_pattern, scanning_normalized):
            return True, "exact_full_name", 1.0
        
        # LEVEL 2: Full name in [Players: ...] list (high confidence = 0.9)
        players_section_pattern = r'\[players:(.*?)\]'
        players_match = re.search(players_section_pattern, scanning_normalized, re.IGNORECASE)
        if players_match:
            players_text = players_match.group(1)
            player_in_list_pattern = f"\\b{re.escape(player_name_normalized)}\\b"
            if re.search(player_in_list_pattern, players_text):
                return True, "players_list", 0.9
        
        # LEVEL 3: Last name with team context validation (medium confidence = 0.7)
        if ' ' in player_name_normalized:
            lastname = player_name_normalized.split()[-1]
            lastname_pattern = f"\\b{re.escape(lastname)}\\b"
            if re.search(lastname_pattern, scanning_normalized):
                # Context validation: check if this looks like a baseball context
                if validate_baseball_context(scanning_normalized, lastname):
                    return True, "lastname_with_context", 0.7
        
        # LEVEL 4: First name with additional validation (lower confidence = 0.6)
        if ' ' in player_name_normalized:
            firstname = player_name_normalized.split()[0]
            # Only for distinctive first names (length >= 5 to avoid common names like "mike", "john")
            if len(firstname) >= 5:
                firstname_pattern = f"\\b{re.escape(firstname)}\\b"
                if re.search(firstname_pattern, scanning_normalized):
                    if validate_baseball_context(scanning_normalized, firstname):
                        return True, "firstname_with_context", 0.6
        
        # LEVEL 5: No match
        return False, "no_match", 0.0
        
    except re.error as e:
        log_error(f"REGEX ERROR in hierarchical matching for player '{player_name_normalized}': {e}")
        return False, "regex_error", 0.0
    except Exception as e:
        log_error(f"ERROR in hierarchical matching for player '{player_name_normalized}': {e}")
        return False, "error", 0.0

def validate_baseball_context(message_normalized, name_part):
    """
    Validate that this appears to be a baseball context to reduce false positives
    """
    try:
        # Baseball context indicators
        baseball_keywords = {
            'asked', 'player', 'team', 'stats', 'overall', 'projection', 'update',
            'hitting', 'pitching', 'batting', 'era', 'whip', 'ops', 'avg', 'home',
            'runs', 'rbi', 'steals', 'wins', 'saves', 'strikeouts', 'walk',
            'mlb', 'baseball', 'season', 'game', 'fantasy', 'roster', 'lineup',
            'trade', 'waiver', 'draft', 'prospect', 'rookie', 'veteran'
        }
        
        # Check if the message contains baseball-related terms
        words_in_message = set(message_normalized.split())
        baseball_context_count = len(words_in_message.intersection(baseball_keywords))
        
        # Require at least 2 baseball context words for lastname/firstname matches
        return baseball_context_count >= 2
        
    except Exception as e:
        log_error(f"ERROR in validate_baseball_context: {e}")
        return False

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
    
    log_info(f"RECENT MENTION CHECK: Answering channel: {ANSWERING_CHANNEL}")
    log_info(f"RECENT MENTION CHECK: Final channel: {FINAL_ANSWER_CHANNEL}")
    
    for player in players_to_check:
        player_name_normalized = normalize_name(player['name'])
        player_uuid = player['uuid'].lower()
        
        log_info(f"RECENT MENTION CHECK: Checking player '{player['name']}' (normalized: '{player_name_normalized}', uuid: {player_uuid[:8]}...)")
        
        # STEP 1: Check question-reposting channel (answering channel) FIRST
        found_in_answering = False
        answering_message_url = None
        if answering_channel:
            try:
                message_count = 0
                async for message in answering_channel.history(after=time_threshold, limit=RECENT_MENTION_LIMIT):
                    message_count += 1
                    # Only check messages from the bot itself
                    if message.author == guild.me:  # guild.me is the bot
                        message_normalized = normalize_name(message.content)
                        
                        # 🔧 ENHANCED DEBUG: Log each message content for Francisco Lindor
                        if 'francisco' in player_name_normalized.lower() or 'lindor' in player_name_normalized.lower():
                            log_info(f"🔧 LINDOR DEBUG: Checking bot message: '{message.content[:200]}...'")
                            log_info(f"🔧 LINDOR DEBUG: Normalized: '{message_normalized[:200]}...'")
                            log_info(f"🔧 LINDOR DEBUG: Looking for: '{player_name_normalized}' or '{player_uuid[:8]}'")
                        
                        # 🔧 FIXED: Add error handling for hierarchical matching
                        try:
                            is_match, match_type, confidence = check_player_mention_hierarchical(
                                player_name_normalized, player_uuid, message_normalized, message.content, 
                                message_author_name=message.author.display_name
                            )
                            
                            if is_match:
                                log_info(f"RECENT MENTION CHECK: Found {player['name']} in bot message in answering channel ({match_type}, confidence: {confidence})")
                                log_info(f"RECENT MENTION CHECK: Match details - player_normalized: '{player_name_normalized}', message_snippet: '{message_normalized[:100]}...'")
                                found_in_answering = True
                                answering_message_url = message.jump_url  # 🔧 CAPTURE THE MESSAGE URL
                                
                                # BYPASS WEBHOOK - Direct Discord message for debugging
                                try:
                                    logs_channel = discord.utils.get(guild.text_channels, name="bernie-stock-logs")
                                    if logs_channel:
                                        await logs_channel.send(f"🔧 **DEBUG**: found_in_answering = True for {player['name']}")
                                except:
                                    pass  # Don't let debug messages break the bot
                                
                                break
                        except Exception as e:
                            log_error(f"ERROR in hierarchical matching for message in answering channel: {e}")
                            continue
                            
                log_info(f"RECENT MENTION CHECK: Checked {message_count} messages in answering channel")
            except Exception as e:
                log_error(f"RECENT MENTION CHECK: Error checking answering channel: {e}")
        
        # STEP 2: ONLY if found in question-reposting, THEN check answered-by-expert
        status = None
        answer_message_url = None
        if found_in_answering:
            log_info(f"RECENT MENTION CHECK: {player['name']} found in question-reposting, now checking answered-by-expert")
            
            # Check final answer channel for BOT messages only
            found_in_final = False
            if final_channel:
                try:
                    message_count = 0
                    async for message in final_channel.history(after=time_threshold, limit=RECENT_MENTION_LIMIT):
                        message_count += 1
                        # Only check messages from the bot itself
                        if message.author == guild.me:  # guild.me is the bot
                            message_normalized = normalize_name(message.content)
                            
                            # 🔧 FIXED: Add error handling for hierarchical matching
                            try:
                                is_match, match_type, confidence = check_player_mention_hierarchical(
                                    player_name_normalized, player_uuid, message_normalized, message.content,
                                    message_author_name=message.author.display_name
                                )
                                
                                if is_match:
                                    log_info(f"RECENT MENTION CHECK: Found {player['name']} in bot message in final channel ({match_type}, confidence: {confidence})")
                                    log_info(f"RECENT MENTION CHECK: Match details - player_normalized: '{player_name_normalized}', message_snippet: '{message_normalized[:100]}...'")
                                    found_in_final = True
                                    answer_message_url = message.jump_url  # 🔧 CAPTURE THE ANSWER MESSAGE URL
                                    
                                    # BYPASS WEBHOOK - Direct Discord message for debugging
                                    try:
                                        logs_channel = discord.utils.get(guild.text_channels, name="bernie-stock-logs")
                                        if logs_channel:
                                            await logs_channel.send(f"🔧 **DEBUG**: found_in_final = True for {player['name']}")
                                    except:
                                        pass  # Don't let debug messages break the bot
                                    
                                    break
                            except Exception as e:
                                log_error(f"ERROR in hierarchical matching for message in final channel: {e}")
                                continue
                                
                    log_info(f"RECENT MENTION CHECK: Checked {message_count} messages in final channel")
                except Exception as e:
                    log_error(f"RECENT MENTION CHECK: Error checking final channel: {e}")
            
            # Determine status based on your vision:
            # Found in question-reposting + found in answered = "answered"
            # Found in question-reposting + NOT found in answered = "pending"
            if found_in_final:
                status = "answered"  # Asked and answered
                log_info(f"RECENT MENTION CHECK: {player['name']} found in both channels - status: answered")
                log_info(f"RECENT MENTION CHECK: Answer URL captured: {answer_message_url}")
            else:
                status = "pending"   # Asked but not answered yet
                log_info(f"RECENT MENTION CHECK: {player['name']} found in question-reposting but not answered - status: pending")
        else:
            log_info(f"RECENT MENTION CHECK: {player['name']} NOT FOUND in question-reposting channel - skipping answered-by-expert check")
            # status remains None - no recent mention, no need to check final channel
        
        # BYPASS WEBHOOK - Direct Discord message for status processing
        try:
            logs_channel = discord.utils.get(guild.text_channels, name="bernie-stock-logs")
            if logs_channel:
                await logs_channel.send(f"🔧 **DEBUG**: Processing {player['name']} - answering: {found_in_answering}, final: {'checked' if found_in_answering else 'skipped'}")
        except:
            pass
        
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
                # 🔧 ENHANCED: Include message URLs in the return data
                mention_data = {
                    "player": player,
                    "status": status,
                    "answering_url": answering_message_url,  # URL to question in #question-reposting
                }
                
                # 🔧 ONLY include answer_url if status is "answered"
                if status == "answered" and answer_message_url:
                    mention_data["answer_url"] = answer_message_url  # URL to answer in #answered-by-expert
                
                recent_mentions.append(mention_data)
                log_info(f"RECENT MENTION CHECK: Added recent mention: {player['name']} ({player['team']}) - {status}")
                
                # BYPASS WEBHOOK - Direct Discord message for adding to results
                try:
                    logs_channel = discord.utils.get(guild.text_channels, name="bernie-stock-logs")
                    if logs_channel:
                        await logs_channel.send(f"🔧 **DEBUG**: ADDED to results: {player['name']} ({player['team']}) - {status}")
                        if status == "answered" and answer_message_url:
                            await logs_channel.send(f"🔧 **DEBUG**: Answer URL: {answer_message_url}")
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