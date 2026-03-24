import re
import asyncio
import logging
from datetime import datetime
from difflib import SequenceMatcher
from config import players_data
from utils import normalize_name, expand_nicknames, is_likely_player_request
from logging_system import log_analytics, log_info
from player_matching_validator import validate_player_matches

# Set up detection tracing logger
logger = logging.getLogger(__name__)


# -------- SEGMENT CLEANING --------

def clean_segment_for_player_matching(segment):
    """🔧 ENHANCED: Clean segments of context words that aren't player names"""
    # Remove common context words that contaminate player name segments
    context_words = {
        'go', 'going', 'diamond', 'diamonds', 'gold', 'silver', 'bronze',
        'will', 'would', 'should', 'could', 'can', 'may', 'might',
        'be', 'being', 'been', 'is', 'are', 'was', 'were',
        'have', 'has', 'had', 'do', 'does', 'did', 'doing',  # Added 'doing'
        'get', 'getting', 'got', 'make', 'making', 'made',
        'take', 'taking', 'took', 'give', 'giving', 'gave',
        'come', 'coming', 'came', 'see', 'seeing', 'saw',
        'know', 'knowing', 'knew', 'think', 'thinking', 'thought',
        'want', 'wanting', 'wanted', 'need', 'needing', 'needed',
        'like', 'liking', 'liked', 'love', 'loving', 'loved',
        'help', 'helping', 'helped', 'try', 'trying', 'tried',
        'work', 'working', 'worked', 'play', 'playing', 'played',
        'look', 'looking', 'looked', 'find', 'finding', 'found',
        'feel', 'feeling', 'felt', 'seem', 'seeming', 'seemed',
        'become', 'becoming', 'became', 'leave', 'leaving', 'left',
        'move', 'moving', 'moved', 'turn', 'turning', 'turned',
        'start', 'starting', 'started', 'stop', 'stopping', 'stopped',
        'keep', 'keeping', 'kept', 'hold', 'holding', 'held',
        'bring', 'bringing', 'brought', 'put', 'putting',
        'set', 'setting', 'run', 'running', 'ran',
        'walk', 'walking', 'walked', 'talk', 'talking', 'talked',
        'ask', 'asking', 'asked', 'tell', 'telling', 'told',
        'show', 'showing', 'showed', 'hear', 'hearing', 'heard',
        'read', 'reading', 'write', 'writing', 'wrote',
        'sit', 'sitting', 'sat', 'stand', 'standing', 'stood',
        'win', 'winning', 'won', 'lose', 'losing', 'lost',
        'buy', 'buying', 'bought', 'sell', 'selling', 'sold',
        'pay', 'paying', 'paid', 'cost', 'costing',
        'spend', 'spending', 'spent', 'save', 'saving', 'saved',
        'open', 'opening', 'opened', 'close', 'closing', 'closed',
        'cut', 'cutting', 'break', 'breaking', 'broke', 'broken',
        'build', 'building', 'built', 'grow', 'growing', 'grew',
        'change', 'changing', 'changed', 'happen', 'happening', 'happened',
        'live', 'living', 'lived', 'die', 'dying', 'died',
        'kill', 'killing', 'killed', 'eat', 'eating', 'ate',
        'drink', 'drinking', 'drank', 'sleep', 'sleeping', 'slept',
        'wake', 'waking', 'woke', 'drive', 'driving', 'drove',
        'ride', 'riding', 'rode', 'fly', 'flying', 'flew',
        'swim', 'swimming', 'swam', 'dance', 'dancing', 'danced',
        'sing', 'singing', 'sang', 'laugh', 'laughing', 'laughed',
        'cry', 'crying', 'cried', 'smile', 'smiling', 'smiled',
        # Question words and punctuation
        'what', 'when', 'where', 'why', 'who', 'how',
        'which', 'whose', 'whom', 'whether',
        # Common endings that indicate context
        '?', '!', '.', ',', ';', ':', '"', "'",
        # Fantasy baseball specific context
        'fantasy', 'points', 'score', 'scoring', 'stats', 'statistics',
        'projection', 'projections', 'value', 'worth', 'price', 'cost',
        'draft', 'drafting', 'drafted', 'pick', 'picking', 'picked',
        'trade', 'trading', 'traded', 'drop', 'dropping', 'dropped',
        'add', 'adding', 'added', 'waiver', 'waivers', 'wire',
        'roster', 'lineup', 'bench', 'start', 'starter', 'starting',
        'sit', 'bench', 'benching', 'benched'
    }
    
    # Split segment into words
    words = segment.lower().split()
    
    # Filter out context words and punctuation
    cleaned_words = []
    for word in words:
        # Remove punctuation from word
        clean_word = re.sub(r'[^\w\s]', '', word)
        
        # Keep word if it's not a context word and has reasonable length
        if (clean_word not in context_words and 
            len(clean_word) >= 3 and 
            clean_word.isalpha()):
            cleaned_words.append(clean_word)
    
    # Return cleaned segment
    cleaned_segment = ' '.join(cleaned_words)
    
    # If cleaning removed everything, return the original (but trimmed)
    if not cleaned_segment.strip():
        return segment.strip()
    
    return cleaned_segment

# -------- NAME EXTRACTION --------

def find_exact_player_matches(text):
    """🔧 SURGICAL FIX #1: Check for exact player name matches first"""
    text_normalized = normalize_name(text)
    exact_matches = []
    
    for player in players_data:
        player_name_normalized = normalize_name(player['name'])
        if player_name_normalized == text_normalized:
            exact_matches.append(player)
            log_info(f"EXACT MATCH FOUND: '{text}' → {player['name']} ({player['team']})")
    
    return exact_matches

def extract_potential_names(text):
    """🔧 SURGICAL FIX #1: Enhanced name extraction with exact match priority"""
    # First expand nicknames
    expanded_text = expand_nicknames(text)
    if expanded_text != text:
        log_info(f"NAME EXTRACTION: Expanded '{text}' to '{expanded_text}'")
        text = expanded_text
    
    # 🔧 SURGICAL FIX #1: Try exact matches FIRST to prevent splitting
    exact_matches = find_exact_player_matches(text)
    if exact_matches:
        log_info(f"EXACT MATCH PRIORITY: Found {len(exact_matches)} exact matches, stopping name extraction")
        return [normalize_name(text)]  # Return only the exact match, don't split
    
    # 🔧 CRITICAL FIX: Word-boundary aware splitting to prevent "Corey" → "C" + "ey"
    # Split on word-boundary separators only, not characters within words
    segments = re.split(r'\s+(?:and|&|vs\.?|versus|or)\s+|\s*[,/\(\)\[\];]\s*', text, flags=re.IGNORECASE)
    
    potential_names = []
    
    # Now normalize each segment individually
    if len(segments) > 1:
        log_info(f"MULTI-PLAYER: Split '{text}' into {len(segments)} segments: {segments}")
        
        # Process each segment individually and normalize
        for i, segment in enumerate(segments):
            # 🔧 CRITICAL FIX: Clean segments of context words before normalizing
            segment_cleaned = clean_segment_for_player_matching(segment.strip())
            segment_normalized = normalize_name(segment_cleaned)
            if len(segment_normalized) >= 3:  # Reasonable minimum length
                potential_names.append(segment_normalized)
                log_info(f"MULTI-PLAYER: Segment {i+1}: '{segment}' → '{segment_cleaned}' → '{segment_normalized}'")
    
    # For single segment (no separators found), use the original logic
    text_normalized = normalize_name(text)
    
    # EXPANDED: Remove common question words and phrases
    stop_words = {
        'how', 'is', 'was', 'are', 'were', 'doing', 'playing', 'performed', 
        'the', 'a', 'an', 'about', 'what', 'when', 'where', 'why', 'who',
        'should', 'would', 'could', 'can', 'will', 'today', 'yesterday',
        'tomorrow', 'this', 'that', 'these', 'those', 'season', 'year', 
        'game', 'games', 'update', 'on', 'for', 'with', 'any', 'get', 'stats',
        'more', 'like', 'than', 'then', 'just', 'only', 'also', 'even',
        'much', 'many', 'some', 'all', 'most', 'best', 'worst', 'better', 'worse',
        'has', 'have', 'had', 'his', 'her', 'him', 'them', 'they', 'their',
        'been', 'being', 'be', 'am', 'as', 'at', 'an', 'or', 'if', 'it',
        'up', 'out', 'in', 'to', 'of', 'my', 'me', 'we', 'us', 'you', 'your',
        # CRITICAL: Add the problematic words we saw in logs
        'kill', 'quiet', 'hope', 'sure', 'doesnt', 'somehow', 'huh', 'day',
        'today', 'nice', 'good', 'bad', 'cool', 'awesome', 'great', 'terrible',
        'amazing', 'fantastic', 'horrible', 'perfect', 'awful', 'wonderful',
        'excellent', 'outstanding', 'impressive', 'please', 'thanks', 'thank',
        'sorry', 'excuse', 'hello', 'hey', 'hi', 'bye', 'goodbye', 'yes', 'no',
        'yeah', 'yep', 'nope', 'okay', 'ok', 'alright', 'right', 'wrong',
        'true', 'false', 'maybe', 'perhaps', 'probably', 'definitely',
        'absolutely', 'certainly', 'obviously', 'clearly', 'exactly', 'really',
        'very', 'quite', 'pretty', 'rather', 'somewhat', 'fairly', 'totally',
        'completely', 'entirely', 'fully', 'mostly', 'largely', 'mainly',
        'basically', 'essentially', 'generally', 'usually', 'normally',
        'typically', 'often', 'sometimes', 'rarely', 'never', 'always',
        # CRITICAL: Add more context words that should be filtered
        'looking', 'numbers', 'projections', 'projection', 'statistics'
    }
    
    # ENHANCED: Increase minimum length requirement for individual words
    min_word_length = 4  # Reduced back to 4 to allow "seth" and "lugo"
    
    # Split into words and remove stop words
    words = text_normalized.split()
    filtered_words = [w for w in words if w not in stop_words and len(w) >= min_word_length]
    
    # 🔧 CRITICAL FIX: Look for 2-word combinations that might be names (like "Alex Vesia")
    # Use original words (not just filtered) to catch names that might include shorter words
    original_words = text_normalized.split()
    
    # First, try combinations from filtered words (higher quality)
    for i in range(len(filtered_words) - 1):
        name_combo = f"{filtered_words[i]} {filtered_words[i+1]}"
        if len(name_combo) >= 7:  # Minimum reasonable full name length
            potential_names.append(name_combo)
    
    # 🔧 ENHANCED: Expanded non-name words and stricter criteria for individual words
    non_name_words = {
        'stats', 'news', 'info', 'question', 'playing', 'game', 'season', 'year', 'team',
        'downdate', 'upgrade', 'downgrade', 'update', 'like', 'more', 'less', 'better', 'worse',
        'good', 'bad', 'nice', 'cool', 'awesome', 'great', 'terrible', 'amazing', 'fantastic',
        'horrible', 'perfect', 'awful', 'wonderful', 'excellent', 'outstanding', 'impressive',
        'doing', 'going', 'coming', 'looking', 'getting', 'having', 'being', 'seeing',
        'thinking', 'feeling', 'knowing', 'saying', 'telling', 'asking', 'giving', 'taking',
        # CRITICAL: Add more problematic words
        'quiet', 'somehow', 'doesnt', 'players', 'player', 'baseball', 'football', 'basketball',
        'hockey', 'soccer', 'sports', 'athlete', 'athletes', 'roster', 'trade', 'trades',
        'draft', 'drafts', 'contract', 'contracts', 'salary', 'salaries', 'money', 'dollars',
        'worth', 'value', 'performance', 'talent', 'skill', 'skills', 'ability', 'abilities'
    }

    # 🔧 NEW: Also try combinations from original words to catch names like "Alex Vesia"
    for i in range(len(original_words) - 1):
        word1, word2 = original_words[i], original_words[i+1]
        
        # Skip if both words are stop words
        if word1 in stop_words and word2 in stop_words:
            continue
            
        # Skip if either word is too short
        if len(word1) < 3 or len(word2) < 3:
            continue
            
        # Skip if either word is clearly not a name
        if word1 in non_name_words or word2 in non_name_words:
            continue
            
        name_combo = f"{word1} {word2}"
        if len(name_combo) >= 7 and name_combo not in potential_names:  # Avoid duplicates
            potential_names.append(name_combo)
            log_info(f"NAME EXTRACTION: Added 2-word combo from original: '{name_combo}'")
    
    # Look for 3-word combinations (like "Juan Soto Jr")
    for i in range(len(filtered_words) - 2):
        name_combo = f"{filtered_words[i]} {filtered_words[i+1]} {filtered_words[i+2]}"
        if len(name_combo) >= 10:  # Minimum reasonable 3-word name length
            potential_names.append(name_combo)

    # STRICTER: Only add individual words if they pass multiple criteria
    for word in filtered_words:
        if (len(word) >= min_word_length and 
            word not in non_name_words and 
            not word.isdigit() and  # No pure numbers
            word.isalpha() and  # Only alphabetic characters
            # NEW: Additional name-like criteria
            word[0].isupper() and  # Should start with capital (names usually do)
            len([c for c in word if c.isupper()]) <= 2):  # Not ALL CAPS or too many caps
            potential_names.append(word)
    
    # Special case: if the input is very short and simple, add it directly (but still filter)
    if len(words) <= 2 and all(len(w) >= min_word_length and w not in stop_words for w in words):
        original_simple = ' '.join(words)
        if original_simple not in potential_names:
            potential_names.append(original_simple)
    
    # Add the original text as fallback (normalized) - but only if it's reasonable length
    # 🔧 CRITICAL FIX: Only add filtered original if it's a single segment (not multi-player)
    if len(segments) <= 1:  # Only for single-segment queries
        original_words = text_normalized.split()
        filtered_original_words = []
        
        for word in original_words:
            # Remove punctuation from word
            clean_word = re.sub(r'[^\w]', '', word)
            # Only keep if it's not a stop word, not a non-name word, and has reasonable length
            if (clean_word and 
                clean_word not in stop_words and 
                clean_word not in non_name_words and 
                len(clean_word) >= 3):
                filtered_original_words.append(clean_word)
        
        if len(filtered_original_words) >= 1:
            filtered_original = ' '.join(filtered_original_words)
            if len(filtered_original.replace(' ', '')) >= 3 and filtered_original not in potential_names:
                potential_names.append(filtered_original)
                log_info(f"NAME EXTRACTION: Added filtered original text: '{filtered_original}'")
    
    # Remove duplicates while preserving order
    unique_names = []
    seen = set()
    for name in potential_names:
        if name not in seen:
            unique_names.append(name)
            seen.add(name)
    
    # 🔧 CLEANUP: Remove names that contain separators (they clutter results and aren't useful for matching)
    separator_chars = [';', '&', '/', '(', ')', '[', ']', ',']
    
    # 🔧 TEAM NAME FILTER: Remove team names that shouldn't be treated as player names
    team_names = {
        # MLB Teams (full names and common abbreviations)
        'angels', 'astros', 'athletics', 'blue jays', 'braves', 'brewers', 'cardinals', 'cubs', 
        'diamondbacks', 'dodgers', 'giants', 'guardians', 'mariners', 'marlins', 'mets', 'nationals',
        'orioles', 'padres', 'phillies', 'pirates', 'rangers', 'rays', 'red sox', 'reds', 'rockies',
        'royals', 'tigers', 'twins', 'white sox', 'yankees',
        # Common abbreviations
        'laa', 'hou', 'oak', 'tor', 'atl', 'mil', 'stl', 'chc', 'ari', 'lad', 'sf', 'cle', 'sea',
        'mia', 'nym', 'was', 'bal', 'sd', 'phi', 'pit', 'tex', 'tb', 'bos', 'cin', 'col', 'kc',
        'det', 'min', 'cws', 'nyy',
        # Other common team references
        'team', 'club', 'organization', 'franchise'
    }
    
    cleaned_names = []
    for name in unique_names:
        # Filter out separator-containing names
        if any(sep in name for sep in separator_chars):
            log_info(f"NAME EXTRACTION: Filtered out separator-containing name: '{name}'")
            continue
        
        # Filter out team names
        if name.lower() in team_names:
            log_info(f"NAME EXTRACTION: Filtered out team name: '{name}'")
            continue
        
        # Keep the name if it passes all filters
        cleaned_names.append(name)
    
    log_info(f"NAME EXTRACTION: Found {len(cleaned_names)} potential names from '{text}': {cleaned_names}")
    return cleaned_names

# -------- LAST NAME MATCHING --------

def check_last_name_match(potential_name, player_name):
    """Special checking for single-word inputs that might be last names"""
    if ' ' in potential_name:  # Only for single words
        return None, False
    
    if len(potential_name) < 3 or len(potential_name) > 12:  # Reasonable last name length
        return None, False
    
    # Get the player's last name
    name_parts = player_name.split()
    if len(name_parts) < 2:
        return None, False
    
    player_last_name = name_parts[-1]
    
    # Check for very close last name match
    similarity = SequenceMatcher(None, potential_name, player_last_name).ratio()
    
    # Special case: if it's a very close match to a last name, be more lenient
    if similarity >= 0.75:  # Lower threshold for last name only
        log_info(f"LAST NAME MATCH: '{potential_name}' vs last name '{player_last_name}' = {similarity:.3f}")
        return similarity, True
    
    return None, False

# -------- FUZZY MATCHING --------

def fuzzy_match_players(text, max_results=8):
    """
    Fuzzy matching with universal protection against long text processing.
    This is the source-level protection that blocks ALL bypass pathways.
    """
    # 🚨 UNIVERSAL PROTECTION: Block long sentences at the source
    word_count = len(text.split())
    if word_count > 3:  # Lowered from 4 to 3 for better protection
        print(f"🚨 BLOCKING fuzzy matching: '{text}' ({word_count} words)")
        log_info(f"BLOCKING fuzzy matching: '{text}' ({word_count} words)")
        return []
    
    # 🚨 VOLUME PROTECTION: Block obviously nonsensical combinations
    nonsensical_words = {'good', 'bad', 'great', 'terrible', 'awesome', 'horrible', 'amazing', 'awful',
                        'is', 'are', 'was', 'were', 'be', 'been', 'being',
                        'the', 'and', 'or', 'but', 'if', 'then', 'when', 'where', 'why', 'how',
                        'very', 'really', 'quite', 'pretty', 'much', 'many', 'some', 'all',
                        'looking', 'going', 'coming', 'getting', 'having', 'doing', 'playing'}
    
    if any(word in text.lower() for word in nonsensical_words):
        print(f"🚨 BLOCKING nonsensical combination: '{text}'")
        log_info(f"BLOCKING nonsensical combination: '{text}'")
        return []
    
    log_info(f"FUZZY MATCH: Starting for '{text}'")
    
    if not players_data:
        log_info(f"FUZZY MATCH: No players data available")
        return []
    
    # Extract potential player names from the text
    potential_names = extract_potential_names(text)
    matches = []
    
    log_info(f"FUZZY MATCH: Testing {len(potential_names)} potential names: {potential_names}")
    
    # Try fuzzy matching with each potential name
    for potential_name in potential_names:
        log_info(f"FUZZY MATCH: Testing potential name: '{potential_name}'")
        
        for i, player in enumerate(players_data):
            player_name = normalize_name(player['name'])
            
            # First check for special last name match
            lastname_sim, is_lastname_match = check_last_name_match(potential_name, player_name)
            
            if is_lastname_match and lastname_sim >= 0.75:
                log_info(f"LAST NAME MATCH: '{potential_name}' → {player['name']} ({player['team']}) = {lastname_sim:.3f}")
                matches.append((player, lastname_sim))
                # Don't continue - still check fuzzy matching for other players
            
            # 🔧 CRITICAL FIX: Enhanced fuzzy matching against individual name parts
            similarity = SequenceMatcher(None, potential_name, player_name).ratio()
            
            # Get all name parts for comparison
            player_name_parts = player_name.split() if ' ' in player_name else [player_name]
            player_first_name = player_name_parts[0] if len(player_name_parts) > 0 else ""
            player_last_name = player_name_parts[-1] if len(player_name_parts) > 0 else ""
            
            # Compare against each name part individually
            name_part_similarities = []
            for name_part in player_name_parts:
                part_similarity = SequenceMatcher(None, potential_name, name_part).ratio()
                name_part_similarities.append(part_similarity)
                if part_similarity == 1.0:  # Exact match with any name part
                    log_info(f"EXACT NAME PART MATCH: '{potential_name}' = '{name_part}' (1.000)")
            
            # Get the best similarity from all comparisons
            best_name_part_similarity = max(name_part_similarities) if name_part_similarities else 0.0
            exact_last_name_match = potential_name == player_last_name
            exact_first_name_match = potential_name == player_first_name
            
            # Use the best similarity from all possible matches
            if exact_last_name_match or exact_first_name_match:
                best_similarity = 1.0
            else:
                best_similarity = max(similarity, best_name_part_similarity)
            
            # Log the comparison details for debugging
            if best_name_part_similarity > similarity:
                log_info(f"NAME PART MATCH BETTER: '{potential_name}' vs '{player_name}' - full: {similarity:.3f}, best part: {best_name_part_similarity:.3f}")
            
            # 🔧 CRITICAL FIX: Enhanced substring detection for BOTH first and last names
            # Check if potential_name is a substring of ANY part of the player's name
            player_name_parts = player_name.split() if ' ' in player_name else [player_name]
            player_first_name = player_name_parts[0] if len(player_name_parts) > 0 else ""
            player_last_name = player_name_parts[-1] if len(player_name_parts) > 0 else ""
            
            # Test both the full potential_name and individual words for substring matches
            is_substring_match = False
            potential_words = potential_name.lower().split()
            
            # 🔧 FIX: Check if any word in potential_name matches ANY part of the player's name
            for word in potential_words:
                if len(word) >= 4:
                    # Check against first name
                    if word in player_first_name.lower():
                        is_substring_match = True
                        log_info(f"SUBSTRING DETECTED: Word '{word}' found in first name '{player_first_name}'")
                        break
                    # Check against last name  
                    elif word in normalize_name(player_last_name):
                        is_substring_match = True
                        log_info(f"SUBSTRING DETECTED: Word '{word}' found in last name '{player_last_name}'")
                        break
                    # Check against any other name parts (middle names, etc.)
                    else:
                        for name_part in player_name_parts:
                            if word in name_part.lower():
                                is_substring_match = True
                                log_info(f"SUBSTRING DETECTED: Word '{word}' found in name part '{name_part}'")
                                break
                        if is_substring_match:
                            break
            
            # Also check if the full potential_name is a substring of any name part
            if not is_substring_match:
                for name_part in player_name_parts:
                    if potential_name.lower() in name_part.lower():
                        is_substring_match = True
                        log_info(f"FULL SUBSTRING DETECTED: '{potential_name}' found in name part '{name_part}'")
                        break
            
            # Dynamic threshold with substring detection
            if exact_last_name_match:
                threshold = 0.7
            elif is_substring_match and len(potential_name) >= 4:
                # 🔧 FIX: Lower threshold for substring matches (like "greene" matching "Riley Greene")
                threshold = 0.6  # Allow Riley Greene (0.667) and Isaiah Greene (0.643) to pass
                log_info(f"SUBSTRING THRESHOLD: Lowered to {threshold} for '{potential_name}' in '{player_last_name}'")
            elif ' ' in potential_name:
                # 🔧 NEW: Much stricter threshold for multi-word queries like "juan soto"
                # This prevents "juan soto" from matching "juan brito" (0.737)
                threshold = 0.95  # Only very close matches for full names
                log_info(f"MULTI-WORD THRESHOLD: Raised to {threshold} for full name '{potential_name}'")
            elif ' ' in player_name and ' ' not in potential_name:
                # Calculate last_name_similarity for threshold logic
                last_name_similarity = SequenceMatcher(None, potential_name, player_last_name).ratio()
                threshold = 0.85 if last_name_similarity < 0.9 else 0.7
            else:
                threshold = 0.7
            
            if best_similarity >= threshold:
                log_info(f"FUZZY MATCH: '{potential_name}' → {player['name']} ({player['team']}) = {best_similarity:.3f} (threshold: {threshold})")
                matches.append((player, best_similarity))
            elif best_similarity >= 0.5:  # Log near misses for debugging
                log_info(f"NEAR MISS: '{potential_name}' → {player['name']} ({player['team']}) = {best_similarity:.3f} (needed: {threshold})")
                # Only log Acuña near misses to avoid spam
                if 'acuna' in normalize_name(player['name']).lower():
                    log_info(f"ACUÑA NEAR MISS", f"'{potential_name}' → {player['name']} ({player['team']}) = {best_similarity:.3f} (needed: {threshold})")
    
    log_info(f"FUZZY MATCH: Found {len(matches)} total matches before deduplication")
    
    # Sort by score and remove duplicates
    matches.sort(key=lambda x: x[1], reverse=True)
    seen_players = set()
    unique_matches = []
    
    for player, score in matches:
        player_key = f"{normalize_name(player['name'])}|{normalize_name(player['team'])}"
        if player_key not in seen_players and len(unique_matches) < max_results:
            log_info(f"ADDING MATCH: {player['name']} ({player['team']}) = {score:.3f}")
            unique_matches.append(player)
            seen_players.add(player_key)
        else:
            if player_key in seen_players:
                log_info(f"DUPLICATE SKIPPED: {player['name']} ({player['team']})")
            else:
                log_info(f"MAX RESULTS REACHED: Skipping {player['name']} ({player['team']})")
    
    log_info(f"FUZZY MATCH: Returning {len(unique_matches)} unique matches")
    return unique_matches

# -------- RAW PLAYER DETECTION (NEW) --------

def capture_all_raw_player_detections(text):
    """
    NEW: Capture ALL player detections before any validation filtering
    This is used for the enhanced blocker message to show what was detected
    Returns: list of detected player names (including false positives)
    """
    start_time = datetime.now()
    
    log_info(f"RAW DETECTION: Capturing all detections for '{text}'")
    
    if not players_data or not is_likely_player_request(text):
        return []
    
    # First, expand any nicknames
    expanded_text = expand_nicknames(text)
    if expanded_text != text:
        log_info(f"RAW DETECTION: Using expanded text: '{expanded_text}'")
        text = expanded_text
    
    text_normalized = normalize_name(text)
    all_detected_names = []
    
    # Stop words to filter out (minimal filtering for raw detection)
    basic_stop_words = {
        'how', 'is', 'was', 'are', 'were', 'the', 'a', 'an', 'about', 'what', 'when', 'where', 'why', 'who',
        'should', 'would', 'could', 'can', 'will', 'today', 'yesterday', 'tomorrow', 'this', 'that', 'these', 'those'
    }
    
    # Extract words with minimal filtering
    words = text_normalized.split()
    filtered_words = [word for word in words if word not in basic_stop_words and len(word) >= 3]
    
    log_info(f"RAW DETECTION: Filtered words: {filtered_words}")
    
    # Test ALL combinations and individual words (no validation filtering)
    
    # Test 2-word combinations
    for i in range(len(filtered_words) - 1):
        combo = f"{filtered_words[i]} {filtered_words[i+1]}"
        
        # Look for matches on this combination
        for player in players_data:
            player_name_normalized = normalize_name(player['name'])
            
            # Check if combo matches or is contained in player name
            if (player_name_normalized == combo or 
                combo in player_name_normalized or 
                player_name_normalized in combo):
                detected_name = player['name']
                if detected_name not in all_detected_names:
                    all_detected_names.append(detected_name)
                    log_info(f"RAW DETECTION: Found combo match '{combo}' → {detected_name}")
    
    # Test 3-word combinations
    for i in range(len(filtered_words) - 2):
        combo = f"{filtered_words[i]} {filtered_words[i+1]} {filtered_words[i+2]}"
        
        # Look for matches on this combination
        for player in players_data:
            player_name_normalized = normalize_name(player['name'])
            
            # Check if combo matches or is contained in player name
            if (player_name_normalized == combo or 
                combo in player_name_normalized or 
                player_name_normalized in combo):
                detected_name = player['name']
                if detected_name not in all_detected_names:
                    all_detected_names.append(detected_name)
                    log_info(f"RAW DETECTION: Found 3-word combo match '{combo}' → {detected_name}")
    
    # Test individual words
    for word in filtered_words:
        # Create variations for possessive/plural forms
        word_variations = [word]
        if word.endswith("'s") and len(word) > 3:
            word_variations.append(word[:-2])
        elif word.endswith("s") and len(word) > 4 and not word.endswith("ss"):
            word_variations.append(word[:-1])
        
        # Test individual word matches
        for player in players_data:
            player_name_normalized = normalize_name(player['name'])
            name_parts = player_name_normalized.split()
            
            # Test all word variations
            for word_variant in word_variations:
                if word_variant in name_parts:
                    detected_name = player['name']
                    if detected_name not in all_detected_names:
                        all_detected_names.append(detected_name)
                        log_info(f"RAW DETECTION: Found individual word match '{word}' → {detected_name}")
                    break
    
    # Test full text matches
    for player in players_data:
        player_name_normalized = normalize_name(player['name'])
        
        # Substring matches
        if (text_normalized in player_name_normalized or 
            player_name_normalized in text_normalized):
            detected_name = player['name']
            if detected_name not in all_detected_names:
                all_detected_names.append(detected_name)
                log_info(f"RAW DETECTION: Found full text match '{text_normalized}' → {detected_name}")
        
        # Lastname matching for single-word queries
        query_words = text_normalized.split()
        if len(query_words) == 1:
            name_parts = player_name_normalized.split()
            if len(name_parts) >= 2:
                lastname = name_parts[-1]
                if re.search(f"\\b{re.escape(lastname)}\\b", text_normalized):
                    detected_name = player['name']
                    if detected_name not in all_detected_names:
                        all_detected_names.append(detected_name)
                        log_info(f"RAW DETECTION: Found lastname match '{lastname}' → {detected_name}")
    
    # 🔧 FIX: Route through simplified detection instead of old complex system
    simplified_matches = simplified_player_detection(text)
    if simplified_matches and isinstance(simplified_matches, list):
        for player in simplified_matches:
            detected_name = player['name']
            if detected_name not in all_detected_names:
                all_detected_names.append(detected_name)
                log_info(f"RAW DETECTION: Found simplified match → {detected_name}")
    elif simplified_matches:
        # Single player returned
        detected_name = simplified_matches['name']
        if detected_name not in all_detected_names:
            all_detected_names.append(detected_name)
            log_info(f"RAW DETECTION: Found simplified match → {detected_name}")
    
    log_info(f"RAW DETECTION: Total detected names: {len(all_detected_names)} - {all_detected_names}")
    return all_detected_names




def check_player_mentioned(text):
    """
    🔄 MAIN ENTRY POINT: Unified player detection with intent-first multi-player blocking
    Returns: 
    - None: No players found
    - List of players: Players found (single or multiple for disambiguation)
    - "BLOCKED": Multi-player query should be blocked
    """
    logger.info(f"🔄 UNIFIED_DETECTION: Starting unified detection for: '{text[:50]}...'")
    
    # STEP 1: Intent-first multi-player detection
    logger.info(f"🔍 INTENT_CHECK: Checking for multi-player intent in: '{text}'")
    has_suspicious_pattern, suspicious_segments = has_multi_player_keywords_enhanced(text)
    
    if has_suspicious_pattern:
        logger.info(f"🔍 INTENT_DETECTED: Multi-player intent found, segments: {suspicious_segments}")
        
        # STEP 2: Strict validation to confirm players
        confirmed_players = validate_suspicious_names_strict(text, suspicious_segments)
        logger.info(f"🔍 VALIDATION_RESULT: {len(confirmed_players)} confirmed players")
        
        if len(confirmed_players) >= 2:
            # Check for different last names
            last_names = set()
            for player in confirmed_players:
                last_name = normalize_name(player['name']).split()[-1]
                last_names.add(last_name)
            
            logger.info(f"🔍 LAST_NAME_CHECK: {len(last_names)} unique last names: {list(last_names)}")
            
            if len(last_names) >= 2:
                # BLOCK: Multiple players with different last names
                logger.info(f"🚫 BLOCKING: Multi-player query with different last names")
                return "BLOCKED"
            else:
                # ALLOW: Same last name = disambiguation
                logger.info(f"✅ ALLOWING: Same last name detected, allowing disambiguation")
                return confirmed_players
        elif len(confirmed_players) == 1:
            # BLOCK: Intent detected but only 1 player confirmed = still multi-player intent
            logger.info(f"🚫 BLOCKING: Multi-player intent with only 1 confirmed player")
            return "BLOCKED"
        else:
            # CONTINUE: Intent detected but no confirmed players
            logger.info(f"✅ CONTINUING: Intent detected but no confirmed players, continuing to normal detection")
    else:
        logger.info(f"✅ NO_INTENT: No multi-player intent detected, continuing with normal detection")
    
    # STEP 3: Normal single-player detection
    logger.info(f"🎯 NORMAL_DETECTION: Running normal player detection")
    result = simplified_player_detection(text)
    
    # Log the result
    if result:
        if isinstance(result, list):
            logger.info(f"🔄 NORMAL_RESULT: Found {len(result)} matches: {[p['name'] for p in result]}")
        else:
            logger.info(f"🔄 NORMAL_RESULT: Found single match: {result['name']}")
    else:
        logger.info(f"🔄 NORMAL_RESULT: No matches found")
    
    return result

def simplified_fuzzy_match(text, max_results=8):
    """
    Enhanced fuzzy matching with suffix-aware logic for names like "Victor Scott" → "Victor Scott II"
    """
    logger.info(f"🎯 SIMPLIFIED_FUZZY: Starting for '{text}'")
    
    if not players_data:
        return []
    
    matches = []
    text_normalized = normalize_name(text).lower()
    name_suffixes = {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}

    for player in players_data:
        player_name = normalize_name(player['name']).lower()
        
        # STRATEGY 1: Direct similarity comparison
        similarity = SequenceMatcher(None, text_normalized, player_name).ratio()
        best_similarity = similarity
        match_strategy = "direct"
        
        # STRATEGY 2: Suffix-aware matching — only when player name has a suffix
        if ' ' in text_normalized and ' ' in player_name:
            player_parts = player_name.split()
            if len(player_parts) > 2 and player_parts[-1] in name_suffixes:
                player_base_name = ' '.join(player_parts[:-1])  # Remove suffix
                base_similarity = SequenceMatcher(None, text_normalized, player_base_name).ratio()
                if base_similarity > best_similarity:
                    best_similarity = base_similarity
                    match_strategy = f"suffix_aware_removed_{player_parts[-1]}"
                    logger.info(f"🎯 SUFFIX_MATCH: '{text_normalized}' vs base '{player_base_name}' = {base_similarity:.3f}")
        
        # STRATEGY 3: Individual name part comparison (for partial matches)
        if ' ' in player_name:
            player_name_parts = player_name.split()
            for name_part in player_name_parts:
                if len(name_part) >= 3:  # Skip very short parts and suffixes
                    part_similarity = SequenceMatcher(None, text_normalized, name_part).ratio()
                    if part_similarity > best_similarity:
                        best_similarity = part_similarity
                        match_strategy = f"name_part_{name_part}"
        
        # STRATEGY 4: Substring matching for exact word matches
        if ' ' in text_normalized:
            text_words = text_normalized.split()
            player_words = player_name.split()
            
            # Count exact word matches
            exact_matches = 0
            total_text_words = len(text_words)
            
            for text_word in text_words:
                if len(text_word) >= 3:  # Only count meaningful words
                    for player_word in player_words:
                        if text_word == player_word:
                            exact_matches += 1
                            break
            
            if exact_matches > 0:
                # Calculate similarity based on exact word matches
                word_match_similarity = exact_matches / total_text_words
                if word_match_similarity > best_similarity:
                    best_similarity = word_match_similarity
                    match_strategy = f"exact_words_{exact_matches}_{total_text_words}"
        
        # Dynamic threshold based on matching strategy and text complexity
        if match_strategy.startswith("suffix_aware"):
            # More lenient for suffix-aware matches
            threshold = 0.85 if ' ' in text_normalized else 0.7
        elif match_strategy.startswith("exact_words"):
            # Very lenient for exact word matches
            threshold = 0.5
        elif ' ' in text_normalized:
            # Standard threshold for multi-word queries
            threshold = 0.90  # Lowered from 0.95
        else:
            # Single word queries
            threshold = 0.7
        
        if best_similarity >= threshold:
            logger.info(f"🎯 SIMPLIFIED_FUZZY: '{text}' → {player['name']} ({player['team']}) = {best_similarity:.3f} (strategy: {match_strategy})")
            matches.append((player, best_similarity))
    
    # Sort by score and remove duplicates
    matches.sort(key=lambda x: x[1], reverse=True)
    seen_players = set()
    unique_matches = []
    
    for player, score in matches:
        player_key = f"{normalize_name(player['name'])}|{normalize_name(player['team'])}"
        if player_key not in seen_players and len(unique_matches) < max_results:
            unique_matches.append(player)
            seen_players.add(player_key)
    
    logger.info(f"🎯 SIMPLIFIED_FUZZY: Returning {len(unique_matches)} matches: {[p['name'] for p in unique_matches]}")
    return unique_matches

def has_multi_player_keywords_enhanced(query):
    """
    SIMPLIFIED: Permissive multi-player detection that only blocks obvious cases.
    Returns: (has_keywords: bool, segments: list)
    """
    query_lower = query.lower()
    
    # 🔧 SIMPLIFIED: Only block on very obvious multi-player keywords
    # Remove complex "or" logic and context-aware detection that causes oscillation
    
    # Clear comparison keywords (always block these)
    comparison_keywords = ['vs', 'versus']
    for keyword in comparison_keywords:
        if f' {keyword} ' in f' {query_lower} ':
            segments = [seg.strip() for seg in re.split(f'\\s+{re.escape(keyword)}\\s+', query, flags=re.IGNORECASE)]
            if len(segments) >= 2:
                log_info(f"SIMPLIFIED INTENT: Found comparison keyword '{keyword}', segments: {segments}")
                return True, segments
    
    # 🔧 PERMISSIVE: Remove "or" detection entirely - too many false positives
    # Users asking "should I start X or Y" are usually asking about one decision, not comparing players
    
    # 🔧 PERMISSIVE: Only block obvious semicolon lists (4+ segments)
    if ';' in query:
        semicolon_segments = [seg.strip() for seg in query.split(';')]
        if len(semicolon_segments) >= 4:  # Require 4+ segments to be very permissive
            name_like_segments = sum(1 for seg in semicolon_segments 
                                   if seg and any(word.isalpha() and len(word) >= 3 for word in seg.split()))
            if name_like_segments >= 4:  # Require 4+ name-like segments
                log_info(f"SIMPLIFIED INTENT: Found obvious semicolon list with {name_like_segments} name-like segments")
                return True, semicolon_segments
    
    # 🔧 REMOVED: Complex comma detection, slash detection, bracket detection
    # These were causing too many false positives
    
    log_info(f"SIMPLIFIED INTENT: No clear multi-player intent detected for: '{query}'")
    return False, []

def validate_suspicious_names_strict(query, suspicious_segments):
    """
    Strict validation using existing systems for Stage 2 confirmation.
    Uses exact matching and existing validation to prevent false positives.
    """
    from player_matching_validator import validate_player_mention_in_text
    
    log_info(f"STRICT VALIDATION: Checking {len(suspicious_segments)} segments for '{query}'")
    
    confirmed_players = []
    
    for segment in suspicious_segments:
        # Try multiple cleaning approaches for better player detection
        cleaning_approaches = [
            segment.strip(),  # Original segment
            clean_segment_for_player_matching(segment),  # Aggressive cleaning
        ]
        
        # Also try extracting just the potential player names
        words = segment.strip().split()
        if len(words) >= 2:
            # Try different combinations to find player names
            cleaning_approaches.append(words[0])  # First word
            cleaning_approaches.append(words[-1])  # Last word (most likely to be player name)
            if len(words) >= 2:
                cleaning_approaches.append(f"{words[0]} {words[1]}")  # First two words
                cleaning_approaches.append(f"{words[-2]} {words[-1]}")  # Last two words
            if len(words) >= 3:
                cleaning_approaches.append(f"{words[-3]} {words[-2]} {words[-1]}")  # Last three words
        elif len(words) == 1:
            cleaning_approaches.append(words[0])  # Single word
        
        log_info(f"STRICT VALIDATION: Processing segment '{segment}' with {len(cleaning_approaches)} approaches")
        
        segment_players = []
        
        for cleaned in cleaning_approaches:
            if not cleaned or len(cleaned.strip()) < 2:
                continue
                
            log_info(f"STRICT VALIDATION: Trying approach: '{segment}' → '{cleaned}'")
            
            # Skip obviously non-name segments
            if not looks_like_player_name(cleaned):
                log_info(f"STRICT VALIDATION: Skipping non-name approach: '{cleaned}'")
                continue
                
            # Use existing exact matching first
            exact_matches = find_exact_player_matches(cleaned)
            
            if exact_matches:
                log_info(f"STRICT VALIDATION: Found {len(exact_matches)} exact matches for '{cleaned}'")
                for player in exact_matches:
                    # Use existing validation system
                    if validate_player_mention_in_text(query, player['name'], context="user_question"):
                        segment_players.append(player)
                        log_info(f"STRICT VALIDATION: Confirmed player: {player['name']}")
                    else:
                        log_info(f"STRICT VALIDATION: Rejected player: {player['name']} (failed validation)")
                break  # Found exact matches, stop trying other approaches
            else:
                # Try simplified fuzzy matching with very strict threshold
                fuzzy_matches = simplified_fuzzy_match(cleaned, max_results=3)
                if fuzzy_matches:
                    log_info(f"STRICT VALIDATION: Found {len(fuzzy_matches)} fuzzy matches for '{cleaned}'")
                    for player in fuzzy_matches:
                        # Use existing validation system
                        if validate_player_mention_in_text(query, player['name'], context="user_question"):
                            segment_players.append(player)
                            log_info(f"STRICT VALIDATION: Confirmed fuzzy player: {player['name']}")
                        else:
                            log_info(f"STRICT VALIDATION: Rejected fuzzy player: {player['name']} (failed validation)")
                    if segment_players:  # Found some players, stop trying other approaches
                        break
        
        confirmed_players.extend(segment_players)
    
    # Remove duplicates
    seen_players = set()
    unique_confirmed = []
    for player in confirmed_players:
        player_key = f"{normalize_name(player['name'])}|{normalize_name(player['team'])}"
        if player_key not in seen_players:
            unique_confirmed.append(player)
            seen_players.add(player_key)
    
    log_info(f"STRICT VALIDATION: Confirmed {len(unique_confirmed)} unique players: {[p['name'] for p in unique_confirmed]}")
    return unique_confirmed

def looks_like_player_name(segment):
    """
    Quick heuristic to filter out obviously non-name segments before any matching.
    """
    segment_lower = segment.lower().strip()
    
    # Obvious non-names
    non_name_phrases = {
        'bench', 'sit', 'start', 'drop', 'add', 'trade', 'keep', 'hold',
        'him', 'her', 'them', 'it', 'this', 'that', 'these', 'those',
        'today', 'tomorrow', 'yesterday', 'now', 'later', 'soon',
        'good', 'bad', 'better', 'worse', 'best', 'worst',
        'stats', 'numbers', 'projections', 'value', 'points',
        'looking', 'doing', 'going', 'playing', 'performing'
    }
    
    if segment_lower in non_name_phrases:
        return False
        
    # Must have reasonable name characteristics
    words = segment.split()
    if len(words) > 3:  # Names rarely have more than 3 words
        return False
        
    # Must have alphabetic content
    if not any(word.isalpha() and len(word) >= 2 for word in words):
        return False
        
    return True


def simplified_player_detection(text):
    """
    Simplified, unified player detection that eliminates competing pathways.
    Single detection flow with clear priority hierarchy.
    """
    start_time = datetime.now()
    
    logger.info(f"🎯 SIMPLIFIED_DETECTION: Starting detection for '{text}'")
    
    if not players_data or not is_likely_player_request(text):
        return None
    
    # Expand nicknames first
    expanded_text = expand_nicknames(text)
    if expanded_text != text:
        logger.info(f"🎯 SIMPLIFIED_DETECTION: Expanded '{text}' to '{expanded_text}'")
        text = expanded_text
    
    # PRIORITY 1: Exact matches (highest priority)
    exact_matches = find_exact_player_matches(text)
    if exact_matches:
        logger.info(f"🎯 SIMPLIFIED_DETECTION: Found {len(exact_matches)} exact matches, returning immediately")
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        asyncio.create_task(log_analytics("Player Search",
            question=text, duration_ms=duration_ms, players_checked=len(players_data),
            matches_found=len(exact_matches), players_found=exact_matches, search_type="exact_match"
        ))
        return exact_matches
    
    # PRIORITY 2: Filtered name extraction and matching
    potential_names = extract_potential_names(text)
    logger.info(f"🎯 SIMPLIFIED_DETECTION: Extracted {len(potential_names)} potential names: {potential_names}")
    
    all_matches = []
    for potential_name in potential_names:
        logger.info(f"🎯 SIMPLIFIED_DETECTION: Processing potential name: '{potential_name}'")
        
        # Use simplified fuzzy matching for each potential name
        name_matches = simplified_fuzzy_match(potential_name, max_results=5)
        if name_matches:
            logger.info(f"🎯 SIMPLIFIED_DETECTION: Found {len(name_matches)} matches for '{potential_name}': {[p['name'] for p in name_matches]}")
            all_matches.extend(name_matches)
    
    # Remove duplicates
    if all_matches:
        seen_players = set()
        unique_matches = []
        for player in all_matches:
            player_key = f"{normalize_name(player['name'])}|{normalize_name(player['team'])}"
            if player_key not in seen_players:
                unique_matches.append(player)
                seen_players.add(player_key)
        
        logger.info(f"🎯 SIMPLIFIED_DETECTION: Found {len(unique_matches)} unique matches before validation")
        
        # PRIORITY 3: Validation
        validated_matches = validate_player_matches(text, unique_matches)
        logger.info(f"🎯 SIMPLIFIED_DETECTION: Validation: {len(unique_matches)} → {len(validated_matches)}")
        
        if validated_matches:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            try:
                asyncio.create_task(log_analytics("Player Search",
                    question=text, duration_ms=duration_ms, players_checked=len(players_data),
                    matches_found=len(validated_matches), players_found=validated_matches, search_type="filtered_detection"
                ))
            except RuntimeError:
                # No event loop running (test environment) - skip analytics
                pass
            return validated_matches
    
    # No matches found
    logger.info(f"🎯 SIMPLIFIED_DETECTION: No matches found for '{text}'")
    duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    
    # 🔧 FIX: Handle asyncio gracefully in test environments
    try:
        asyncio.create_task(log_analytics("Player Search",
            question=text, duration_ms=duration_ms, players_checked=len(players_data),
            matches_found=0, search_type="no_match"
        ))
    except RuntimeError:
        # No event loop running (test environment) - skip analytics
        pass
    
    return None
