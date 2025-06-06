import re
import discord
from datetime import datetime, timedelta, timezone
from config import FINAL_ANSWER_CHANNEL, ANSWERING_CHANNEL, RECENT_MENTION_HOURS, RECENT_MENTION_LIMIT
from utils import normalize_name
from logging_system import log_error, log_info
from player_matching_validator import validate_player_matches

# -------- ENHANCED MESSAGE PARSING FUNCTIONS --------

def parse_final_answer_sections(message_content):
    """
    Parse final answer message into sections to prioritize expert reply content
    Returns: {
        'expert_reply': str,      # Clean expert answer content (highest priority)
        'question_content': str,  # Question without metadata (medium priority) 
        'metadata': str,          # [Players: ...] sections (lowest priority)
        'full_message': str       # Fallback to full message
    }
    """
    try:
        # Initialize sections
        sections = {
            'expert_reply': '',
            'question_content': '',
            'metadata': '',
            'full_message': message_content
        }
        
        # Split message by the standard pattern: **Expert** replied:
        expert_reply_pattern = r'\*\*([^*]+)\*\* replied:\s*'
        expert_match = re.search(expert_reply_pattern, message_content, re.IGNORECASE)
        
        if expert_match:
            # Extract question section (everything before expert reply)
            question_section = message_content[:expert_match.start()].strip()
            
            # Extract expert reply section (everything after "replied:")
            expert_reply_raw = message_content[expert_match.end():].strip()
            
            # Clean expert reply: remove correction footer if present
            correction_pattern = r'\*This answer was corrected by [^*]+\*\s*$'
            expert_reply_clean = re.sub(correction_pattern, '', expert_reply_raw, flags=re.IGNORECASE).strip()
            
            # Remove any trailing "-----" markers
            expert_reply_clean = re.sub(r'-+\s*$', '', expert_reply_clean).strip()
            
            sections['expert_reply'] = expert_reply_clean
            
            # Parse question section to separate content from metadata
            if question_section:
                # Extract [Players: ...] metadata from question
                metadata_pattern = r'\[Players?:[^\]]+\]'
                metadata_matches = re.findall(metadata_pattern, question_section, re.IGNORECASE)
                sections['metadata'] = ' '.join(metadata_matches)
                
                # Remove metadata from question to get clean question content
                question_clean = re.sub(metadata_pattern, '', question_section, flags=re.IGNORECASE)
                # Also remove the "**Question:**" header and user mention
                question_clean = re.sub(r'\*\*Question:\*\*\s*', '', question_clean, flags=re.IGNORECASE)
                question_clean = re.sub(r'<@\d+>\s*asked:\s*', '', question_clean, flags=re.IGNORECASE)
                sections['question_content'] = question_clean.strip()
            
            log_info(f"MESSAGE PARSING: Successfully parsed message sections")
            log_info(f"MESSAGE PARSING: Expert reply length: {len(sections['expert_reply'])}")
            log_info(f"MESSAGE PARSING: Question content length: {len(sections['question_content'])}")
            log_info(f"MESSAGE PARSING: Metadata length: {len(sections['metadata'])}")
            
        else:
            # No clear expert reply structure found, treat as legacy format
            log_info(f"MESSAGE PARSING: No expert reply pattern found, using full message")
            sections['expert_reply'] = message_content
            sections['question_content'] = message_content
        
        return sections
        
    except Exception as e:
        log_error(f"ERROR in parse_final_answer_sections: {e}")
        # Fallback to treating entire message as expert reply
        return {
            'expert_reply': message_content,
            'question_content': message_content,
            'metadata': '',
            'full_message': message_content
        }

def check_player_in_message_sections(player_name_normalized, player_uuid, sections, message_author_name=None):
    """
    Check for player mentions across message sections with weighted priority
    Returns: (is_match, match_type, confidence_score, section_found)
    """
    try:
        # PRIORITY 1: Check expert reply section (highest confidence)
        if sections['expert_reply']:
            expert_normalized = normalize_name(sections['expert_reply'])
            is_match, match_type, confidence = check_player_mention_hierarchical(
                player_name_normalized, player_uuid, expert_normalized, sections['expert_reply'], message_author_name
            )
            if is_match:
                log_info(f"SECTION MATCH: Found {player_name_normalized} in EXPERT REPLY ({match_type}, confidence: {confidence})")
                return True, f"expert_reply_{match_type}", confidence, "expert_reply"
        
        # PRIORITY 2: Check question content (medium confidence)
        if sections['question_content']:
            question_normalized = normalize_name(sections['question_content'])
            is_match, match_type, confidence = check_player_mention_hierarchical(
                player_name_normalized, player_uuid, question_normalized, sections['question_content'], message_author_name
            )
            if is_match:
                # Reduce confidence for question-only matches
                reduced_confidence = confidence * 0.5
                log_info(f"SECTION MATCH: Found {player_name_normalized} in QUESTION CONTENT ({match_type}, confidence: {reduced_confidence})")
                return True, f"question_{match_type}", reduced_confidence, "question_content"
        
        # PRIORITY 3: Check metadata (lowest confidence)
        if sections['metadata']:
            metadata_normalized = normalize_name(sections['metadata'])
            is_match, match_type, confidence = check_player_mention_hierarchical(
                player_name_normalized, player_uuid, metadata_normalized, sections['metadata'], message_author_name
            )
            if is_match:
                # Significantly reduce confidence for metadata-only matches
                reduced_confidence = confidence * 0.2
                log_info(f"SECTION MATCH: Found {player_name_normalized} in METADATA ({match_type}, confidence: {reduced_confidence})")
                return True, f"metadata_{match_type}", reduced_confidence, "metadata"
        
        # No match found in any section
        return False, "no_match", 0.0, "none"
        
    except Exception as e:
        log_error(f"ERROR in check_player_in_message_sections: {e}")
        # Fallback to full message check
        full_normalized = normalize_name(sections['full_message'])
        return check_player_mention_hierarchical(
            player_name_normalized, player_uuid, full_normalized, sections['full_message'], message_author_name
        ) + ("fallback",)

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
    Enhanced hierarchical matching with phrase validation
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
                            # Apply phrase validation even to exact matches to catch false positives
                            mock_player = {'name': player_name_normalized, 'team': 'Unknown'}
                            validated_matches = validate_player_matches(scanning_normalized, [mock_player], context="expert_reply")
                            if validated_matches:
                                return True, "exact_full_name_validated", 1.0
                            else:
                                log_info(f"RECENT MENTION VALIDATION: Exact match for '{player_name_normalized}' rejected by phrase validation")
                                return False, "exact_full_name_rejected", 0.0
        
        # LEVEL 2: Full name in [Players: ...] list (high confidence = 0.9)
        players_section_pattern = r'\[players:(.*?)\]'
        players_match = re.search(players_section_pattern, scanning_normalized, re.IGNORECASE)
        if players_match:
            players_text = players_match.group(1)
            player_in_list_pattern = f"\\b{re.escape(player_name_normalized)}\\b"
            if re.search(player_in_list_pattern, players_text):
                # Players list matches are generally safe, but still validate
                mock_player = {'name': player_name_normalized, 'team': 'Unknown'}
                validated_matches = validate_player_matches(players_text, [mock_player], context="metadata")
                if validated_matches:
                    return True, "players_list_validated", 0.9
                else:
                    log_info(f"RECENT MENTION VALIDATION: Players list match for '{player_name_normalized}' rejected by phrase validation")
                    return False, "players_list_rejected", 0.0
        
        # LEVEL 3: Last name with enhanced validation (medium confidence = 0.7)
        if ' ' in player_name_normalized:
            lastname = player_name_normalized.split()[-1]
            lastname_pattern = f"\\b{re.escape(lastname)}\\b"
            if re.search(lastname_pattern, scanning_normalized):
                # Enhanced validation: baseball context + phrase validation
                if validate_baseball_context(scanning_normalized, lastname):
                    # Additional phrase validation for lastname matches
                    mock_player = {'name': player_name_normalized, 'team': 'Unknown'}
                    validated_matches = validate_player_matches(scanning_normalized, [mock_player], context="expert_reply")
                    if validated_matches:
                        return True, "lastname_with_context_validated", 0.7
                    else:
                        log_info(f"RECENT MENTION VALIDATION: Lastname match for '{lastname}' rejected by phrase validation")
                        return False, "lastname_context_rejected", 0.0
        
        # LEVEL 4: First name with enhanced validation (lower confidence = 0.6)
        if ' ' in player_name_normalized:
            firstname = player_name_normalized.split()[0]
            # Only for distinctive first names (length >= 5 to avoid common names like "mike", "john")
            if len(firstname) >= 5:
                firstname_pattern = f"\\b{re.escape(firstname)}\\b"
                if re.search(firstname_pattern, scanning_normalized):
                    if validate_baseball_context(scanning_normalized, firstname):
                        # Additional phrase validation for firstname matches
                        mock_player = {'name': player_name_normalized, 'team': 'Unknown'}
                        validated_matches = validate_player_matches(scanning_normalized, [mock_player], context="expert_reply")
                        if validated_matches:
                            return True, "firstname_with_context_validated", 0.6
                        else:
                            log_info(f"RECENT MENTION VALIDATION: Firstname match for '{firstname}' rejected by phrase validation")
                            return False, "firstname_context_rejected", 0.0
        
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
        
        # STEP 2: ALWAYS check final answer channel (regardless of answering channel result)
        found_in_final = False
        answer_message_url = None
        if final_channel:
            try:
                message_count = 0
                async for message in final_channel.history(after=time_threshold, limit=RECENT_MENTION_LIMIT):
                    message_count += 1
                    # Only check messages from the bot itself
                    if message.author == guild.me:  # guild.me is the bot
                        message_normalized = normalize_name(message.content)
                        
                        # 🔧 ENHANCED: Use new section-based parsing for final answer messages
                        try:
                            # Parse message into sections
                            sections = parse_final_answer_sections(message.content)
                            
                            # Use enhanced section-based matching
                            is_match, match_type, confidence, section_found = check_player_in_message_sections(
                                player_name_normalized, player_uuid, sections, message.author.display_name
                            )
                            
                            if is_match:
                                # Apply confidence threshold - only count as "answered" if found in expert reply
                                if section_found == "expert_reply" and confidence >= 0.7:
                                    log_info(f"RECENT MENTION CHECK: Found {player['name']} in EXPERT REPLY in final channel ({match_type}, confidence: {confidence})")
                                    found_in_final = True
                                    answer_message_url = message.jump_url
                                    
                                    # BYPASS WEBHOOK - Direct Discord message for debugging
                                    try:
                                        logs_channel = discord.utils.get(guild.text_channels, name="bernie-stock-logs")
                                        if logs_channel:
                                            await logs_channel.send(f"🔧 **DEBUG**: found_in_final = True for {player['name']} (expert reply)")
                                    except:
                                        pass
                                    
                                    break
                                else:
                                    # Found in question/metadata but not expert reply - don't count as answered
                                    log_info(f"RECENT MENTION CHECK: Found {player['name']} in {section_found} but not expert reply (confidence: {confidence}) - not counting as answered")
                                    
                                    # BYPASS WEBHOOK - Direct Discord message for debugging
                                    try:
                                        logs_channel = discord.utils.get(guild.text_channels, name="bernie-stock-logs")
                                        if logs_channel:
                                            await logs_channel.send(f"🔧 **DEBUG**: {player['name']} found in {section_found} but not expert reply - ignoring")
                                    except:
                                        pass
                        except Exception as e:
                            log_error(f"ERROR in hierarchical matching for message in final channel: {e}")
                            continue
                            
                log_info(f"RECENT MENTION CHECK: Checked {message_count} messages in final channel")
            except Exception as e:
                log_error(f"RECENT MENTION CHECK: Error checking final channel: {e}")
        
        # STEP 3: Determine status with correct priority logic
        status = None
        if found_in_final:
            # Priority: If found in final channel = answered (with URL)
            status = "answered"
            log_info(f"RECENT MENTION CHECK: {player['name']} found in final channel - status: answered")
            log_info(f"RECENT MENTION CHECK: Answer URL captured: {answer_message_url}")
        elif found_in_answering:
            # If found only in answering channel = pending
            status = "pending"
            log_info(f"RECENT MENTION CHECK: {player['name']} found only in answering channel - status: pending")
        else:
            log_info(f"RECENT MENTION CHECK: {player['name']} NOT FOUND in either channel - approved")
            # status remains None - no recent mention, question is approved
        
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
    """Enhanced fallback check for recent mentions using potential player words with validation"""
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
                            # Apply phrase validation to fallback matches
                            mock_player = {'name': word, 'team': 'Unknown'}
                            validated_matches = validate_player_matches(message_normalized, [mock_player], context="expert_reply")
                            if validated_matches:
                                log_info(f"FALLBACK: Found '{word}' in recent bot message in answering channel (validated)")
                                return True
                            else:
                                log_info(f"FALLBACK VALIDATION: Word '{word}' found but rejected by phrase validation")
            except Exception as e:
                log_error(f"FALLBACK: Error checking answering channel: {e}")
        
        # Check final channel
        if final_channel:
            try:
                async for message in final_channel.history(after=time_threshold, limit=RECENT_MENTION_LIMIT):
                    if message.author == guild.me:
                        message_normalized = normalize_name(message.content)
                        if word in message_normalized:
                            # Apply phrase validation to fallback matches
                            mock_player = {'name': word, 'team': 'Unknown'}
                            validated_matches = validate_player_matches(message_normalized, [mock_player], context="expert_reply")
                            if validated_matches:
                                log_info(f"FALLBACK: Found '{word}' in recent bot message in final channel (validated)")
                                return True
                            else:
                                log_info(f"FALLBACK VALIDATION: Word '{word}' found but rejected by phrase validation")
            except Exception as e:
                log_error(f"FALLBACK: Error checking final channel: {e}")
    
    return False
