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
    if 'rodon' in player_name_normalized.lower():
        log_info(f"🔍 HIERARCHICAL DEBUG: Checking '{player_name_normalized}' in message: '{message_normalized[:100]}...'")

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
            if 'rodon' in player_name_normalized.lower():
               log_info(f"🔍 LEVEL 1 DEBUG: Found exact match for '{player_name_normalized}' in '{scanning_normalized[:50]}...'")
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
            # 🔧 FIXED: Prevent partial word matches like "last" matching "lasts"
            # Use stricter word boundary pattern that requires exact word match
            lastname_pattern = f"\\b{re.escape(lastname)}\\b(?![a-z])"
            lastname_matches = re.findall(lastname_pattern, scanning_normalized, re.IGNORECASE)
            
            if lastname_matches:
                # Additional check: ensure the found word is exactly the lastname (not a partial match)
                exact_lastname_found = any(match.lower() == lastname.lower() for match in lastname_matches)
                
                if exact_lastname_found:
                    if 'rodon' in player_name_normalized.lower():
                        log_info(f"🔍 LEVEL 3 DEBUG: Found exact lastname '{lastname}' in '{scanning_normalized[:50]}...'")
                        log_info(f"🔍 LEVEL 3 DEBUG: Baseball context check result: {validate_baseball_context(scanning_normalized, lastname)}")
                    
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
                else:
                    log_info(f"RECENT MENTION VALIDATION: Lastname '{lastname}' found but only as partial match - rejecting")
                    return False, "lastname_partial_match_rejected", 0.0
        
        # LEVEL 4: First name with enhanced validation (lower confidence = 0.6)
        if ' ' in player_name_normalized:
            firstname = player_name_normalized.split()[0]
            # Only for distinctive first names (length >= 5 to avoid common names like "mike", "john")
            if len(firstname) >= 5:
                # 🔧 FIXED: Use same stricter pattern as lastname to prevent partial matches
                firstname_pattern = f"\\b{re.escape(firstname)}\\b(?![a-z])"
                firstname_matches = re.findall(firstname_pattern, scanning_normalized, re.IGNORECASE)
                
                if firstname_matches:
                    # Additional check: ensure the found word is exactly the firstname (not a partial match)
                    exact_firstname_found = any(match.lower() == firstname.lower() for match in firstname_matches)
                    
                    if exact_firstname_found and validate_baseball_context(scanning_normalized, firstname):
                        # Additional phrase validation for firstname matches
                        mock_player = {'name': player_name_normalized, 'team': 'Unknown'}
                        validated_matches = validate_player_matches(scanning_normalized, [mock_player], context="expert_reply")
                        if validated_matches:
                            return True, "firstname_with_context_validated", 0.6
                        else:
                            log_info(f"RECENT MENTION VALIDATION: Firstname match for '{firstname}' rejected by phrase validation")
                            return False, "firstname_context_rejected", 0.0
                    else:
                        log_info(f"RECENT MENTION VALIDATION: Firstname '{firstname}' found but only as partial match or failed baseball context - rejecting")
                        return False, "firstname_partial_match_rejected", 0.0
        
        # LEVEL 5: No match
        if 'rodon' in player_name_normalized.lower():
            log_info(f"🔍 NO MATCH DEBUG: '{player_name_normalized}' not found in '{scanning_normalized[:50]}...'")
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
            'trade', 'waiver', 'draft', 'prospect', 'rookie', 'veteran', 'outlook', 
            'status', 'thoughts', 'opinion', 'analysis', 'review',
            'check', 'chances', 'potential', 'doing'
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
        
        # TIER 1: Check question-reposting channel (pending status)
        log_info(f"TIER 1: Checking answering channel for pending questions...")
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
                                break
                        except Exception as e:
                            log_error(f"ERROR in hierarchical matching for message in answering channel: {e}")
                            continue
                            
                log_info(f"RECENT MENTION CHECK: Checked {message_count} messages in answering channel")
            except Exception as e:
                log_error(f"RECENT MENTION CHECK: Error checking answering channel: {e}")
        
        # TIER 2 & 3: Check final answer channel (answered vs mentioned)
        log_info(f"TIER 2 & 3: Checking final channel for answered/mentioned players...")
        found_in_final = False
        answer_message_url = None
        if final_channel:
            try:
                message_count = 0
                async for message in final_channel.history(after=time_threshold, limit=RECENT_MENTION_LIMIT):
                    message_count += 1
                    # Only check messages from the bot itself
                    log_info(f"CHECKING MESSAGE: '{message.content[:100]}...' (ID: {message.id})")
                    if message.author == guild.me:  # guild.me is the bot
                        message_normalized = normalize_name(message.content)
                        
                        # Parse message into sections for tiered checking
                        try:
                            # Parse message into sections
                            sections = parse_final_answer_sections(message.content)
                            
                            # Use enhanced section-based matching
                            is_match, match_type, confidence, section_found = check_player_in_message_sections(
                                player_name_normalized, player_uuid, sections, message.author.display_name
                            )
                            
                            if is_match:
                                # TIER 2: Check if found in expert reply (strong block - answered)
                                if section_found == "expert_reply" and confidence >= 0.7:
                                    log_info(f"TIER 2: Found {player['name']} in EXPERT REPLY - status: answered")
                                    found_in_final = True
                                    answer_message_url = message.jump_url
                                    break
                                else:
                                    # TIER 3: Player not in expert reply, check if mentioned anywhere in full message
                                    full_message_normalized = normalize_name(message.content)
                                    is_full_match, full_match_type, full_confidence = check_player_mention_hierarchical(
                                        player_name_normalized, player_uuid, full_message_normalized, message.content, 
                                        message.author.display_name
                                    )
                                    
                                    if is_full_match and full_confidence >= 0.7:
                                        # Player was mentioned but NOT answered by expert - DON'T BLOCK
                                        log_info(f"TIER 3: {player['name']} mentioned in question but NOT in expert reply - allowing future questions")
                                        # Continue checking other messages, don't set found_in_final = True
                                    # If not found anywhere in this message, continue to next message
                                    
                        except Exception as e:
                            log_error(f"ERROR in hierarchical matching for message in final channel: {e}")
                            continue
                            
                log_info(f"RECENT MENTION CHECK: Checked {message_count} messages in final channel")
            except Exception as e:
                log_error(f"RECENT MENTION CHECK: Error checking final channel: {e}")
        
        # STEP 3: Determine status with tiered logic
        status = None
        if found_in_final:
            # Only set to "answered" if found in expert reply section
            status = "answered"
            log_info(f"RECENT MENTION CHECK: {player['name']} found in expert reply - status: answered")
            log_info(f"RECENT MENTION CHECK: Answer URL captured: {answer_message_url}")
        elif found_in_answering:
            # If found only in answering channel = pending
            status = "pending"
            log_info(f"RECENT MENTION CHECK: {player['name']} found only in answering channel - status: pending")
        else:
            # 🔧 NEW: No blocking status means question gets through
            # This includes cases where player was mentioned in questions but not in expert replies
            log_info(f"RECENT MENTION CHECK: {player['name']} NOT FOUND in expert replies or pending questions - allowing through")
            # status remains None - no recent mention that should block

        # Add to results only if there's a blocking status
        if status:
            # Check for duplicates
            already_added = False
            for existing in recent_mentions:
                if (normalize_name(existing["player"]["name"]) == normalize_name(player["name"]) and 
                    normalize_name(existing["player"]["team"]) == normalize_name(player["team"])):
                    already_added = True
                    log_info(f"RECENT MENTION CHECK: Skipping duplicate recent mention for {player['name']} ({player['team']})")
                    break
            
            if not already_added:
                mention_data = {
                    "player": player,
                    "status": status,
                    "answering_url": answering_message_url,
                }
                
                # Only include answer_url if status is "answered"
                if status == "answered" and answer_message_url:
                    mention_data["answer_url"] = answer_message_url
                
                recent_mentions.append(mention_data)
                log_info(f"RECENT MENTION CHECK: Added recent mention: {player['name']} ({player['team']}) - {status}")
        # If status is None, player is not added to recent_mentions, so question will be allowed
    
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
