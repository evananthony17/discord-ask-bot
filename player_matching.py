import re
import asyncio
from datetime import datetime
from difflib import SequenceMatcher
from config import players_data
from utils import normalize_name, expand_nicknames, is_likely_player_request
from logging_system import log_analytics, log_info

# -------- NAME EXTRACTION --------

def extract_potential_names(text):
    """ENHANCED: Extract potential player names with multi-player detection"""
    # First expand nicknames
    expanded_text = expand_nicknames(text)
    if expanded_text != text:
        log_info(f"NAME EXTRACTION: Expanded '{text}' to '{expanded_text}'")
        text = expanded_text
    
    text_normalized = normalize_name(text)
    potential_names = []
    
    # ENHANCED: Split text by common separators for multi-player detection
    # Split by "and", "&", "vs", "versus", commas, etc.
    segments = re.split(r'\s+(?:and|&|vs\.?|versus|,)\s+', text_normalized, flags=re.IGNORECASE)
    
    if len(segments) > 1:
        log_info(f"MULTI-PLAYER: Split '{text}' into {len(segments)} segments: {segments}")
        
        # Process each segment individually
        for i, segment in enumerate(segments):
            segment = segment.strip()
            if len(segment) >= 3:  # Reasonable minimum length
                potential_names.append(segment)
                log_info(f"MULTI-PLAYER: Segment {i+1}: '{segment}'")
    
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
        'typically', 'often', 'sometimes', 'rarely', 'never', 'always'
    }
    
    # ENHANCED: Increase minimum length requirement for individual words
    min_word_length = 5  # Changed from 4 to 5 to eliminate "kill", "hope", etc.
    
    # Split into words and remove stop words
    words = text_normalized.split()
    filtered_words = [w for w in words if w not in stop_words and len(w) >= min_word_length]
    
    # Look for 2-word combinations that might be names (like "Christian Moore")
    for i in range(len(filtered_words) - 1):
        name_combo = f"{filtered_words[i]} {filtered_words[i+1]}"
        if len(name_combo) >= 7:  # Minimum reasonable full name length
            potential_names.append(name_combo)
    
    # Look for 3-word combinations (like "Juan Soto Jr")
    for i in range(len(filtered_words) - 2):
        name_combo = f"{filtered_words[i]} {filtered_words[i+1]} {filtered_words[i+2]}"
        if len(name_combo) >= 10:  # Minimum reasonable 3-word name length
            potential_names.append(name_combo)
    
    # ENHANCED: Expanded non-name words and stricter criteria for individual words
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
    if len(text_normalized.replace(' ', '')) >= min_word_length:
        potential_names.append(text_normalized)
    
    # Remove duplicates while preserving order
    unique_names = []
    seen = set()
    for name in potential_names:
        if name not in seen:
            unique_names.append(name)
            seen.add(name)
    
    log_info(f"NAME EXTRACTION: Found {len(unique_names)} potential names from '{text}': {unique_names}")
    return unique_names

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
    """FIXED: Fuzzy match player names and return ALL matches above threshold"""
    
    log_info(f"FUZZY MATCH: Starting for '{text}'")
    log_info(f"FUZZY MATCH Starting", f"Query: '{text}'")
    
    if not players_data:
        log_info(f"FUZZY MATCH: No players data available")
        return []
    
    # Extract potential player names from the text
    potential_names = extract_potential_names(text)
    matches = []
    
    log_info(f"FUZZY MATCH: Testing {len(potential_names)} potential names: {potential_names}")
    log_info(f"FUZZY MATCH Potential Names", f"Found {len(potential_names)} names: {potential_names}")
    
    # Try fuzzy matching with each potential name
    for potential_name in potential_names:
        log_info(f"FUZZY MATCH: Testing potential name: '{potential_name}'")
        log_info(f"FUZZY MATCH Testing", f"Name: '{potential_name}'")
        
        for i, player in enumerate(players_data):
            player_name = normalize_name(player['name'])
            
            # First check for special last name match
            lastname_sim, is_lastname_match = check_last_name_match(potential_name, player_name)
            
            if is_lastname_match and lastname_sim >= 0.75:
                log_info(f"LAST NAME MATCH: '{potential_name}' → {player['name']} ({player['team']}) = {lastname_sim:.3f}")
                matches.append((player, lastname_sim))
                continue
            
            # Regular fuzzy matching
            similarity = SequenceMatcher(None, potential_name, player_name).ratio()
            
            # Special handling for last names
            player_last_name = player_name.split()[-1] if ' ' in player_name else player_name
            last_name_similarity = SequenceMatcher(None, potential_name, player_last_name).ratio()
            exact_last_name_match = potential_name == player_last_name
            
            # Use the better of full name match or last name match
            if exact_last_name_match:
                best_similarity = 1.0
            else:
                best_similarity = max(similarity, last_name_similarity)
            
            # Dynamic threshold
            if exact_last_name_match:
                threshold = 0.7
            elif ' ' in player_name and ' ' not in potential_name:
                threshold = 0.85 if last_name_similarity < 0.9 else 0.7
            else:
                threshold = 0.7
            
            if best_similarity >= threshold:
                log_info(f"FUZZY MATCH: '{potential_name}' → {player['name']} ({player['team']}) = {best_similarity:.3f} (threshold: {threshold})")
                log_info(f"FUZZY MATCH Found", f"'{potential_name}' → {player['name']} ({player['team']}) = {best_similarity:.3f}")
                matches.append((player, best_similarity))
            elif best_similarity >= 0.5:  # Log near misses for debugging
                log_info(f"NEAR MISS: '{potential_name}' → {player['name']} ({player['team']}) = {best_similarity:.3f} (needed: {threshold})")
                # Only log Acuña near misses to avoid spam
                if 'acuna' in normalize_name(player['name']).lower():
                    log_info(f"ACUÑA NEAR MISS", f"'{potential_name}' → {player['name']} ({player['team']}) = {best_similarity:.3f} (needed: {threshold})")
    
    log_info(f"FUZZY MATCH: Found {len(matches)} total matches before deduplication")
    log_info(f"FUZZY MATCH Total", f"Found {len(matches)} matches before deduplication")
    
    # Sort by score and remove duplicates
    matches.sort(key=lambda x: x[1], reverse=True)
    seen_players = set()
    unique_matches = []
    
    for player, score in matches:
        player_key = f"{normalize_name(player['name'])}|{normalize_name(player['team'])}"
        if player_key not in seen_players and len(unique_matches) < max_results:
            log_info(f"ADDING MATCH: {player['name']} ({player['team']}) = {score:.3f}")
            log_info(f"FUZZY MATCH Adding", f"{player['name']} ({player['team']}) = {score:.3f}")
            unique_matches.append(player)
            seen_players.add(player_key)
        else:
            if player_key in seen_players:
                log_info(f"DUPLICATE SKIPPED: {player['name']} ({player['team']})")
            else:
                log_info(f"MAX RESULTS REACHED: Skipping {player['name']} ({player['team']})")
    
    log_info(f"FUZZY MATCH: Returning {len(unique_matches)} unique matches")
    log_info(f"FUZZY MATCH Final", f"Returning {len(unique_matches)} unique matches: {[p['name'] for p in unique_matches]}")
    return unique_matches

# -------- MAIN PLAYER CHECKING FUNCTION --------

def check_player_mentioned(text):
    """🔧 FIXED: Check if any player is mentioned with COMBINATION-FIRST matching to avoid false positives"""
    start_time = datetime.now()
    
    log_info(f"CHECK PLAYER: Looking for players in '{text}'")
    
    if not players_data or not is_likely_player_request(text):
        return None
    
    # First, expand any nicknames
    expanded_text = expand_nicknames(text)
    if expanded_text != text:
        log_info(f"NICKNAME: Using expanded text: '{expanded_text}'")
        text = expanded_text
    
    # 🔧 NEW: COMBINATION-FIRST approach to avoid false positives like "Will Cruz"
    text_normalized = normalize_name(text)
    
    # Stop words to filter out
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
        'do', 'go', 'diamond', 'heat', 'cold'  # Added 'heat' and 'cold' to avoid "heat up" issues
    }
    
    # Extract words and filter
    words = text_normalized.split()
    filtered_words = [word for word in words if word not in stop_words and len(word) >= 3]
    
    log_info(f"WORD EXTRACTION: Original text: '{text_normalized}'")
    log_info(f"WORD EXTRACTION: Filtered words: {filtered_words}")
    
    # 🔧 STEP 1: Test COMBINATIONS first (2-word and 3-word phrases)
    combination_matches = []
    
    # Test 2-word combinations
    for i in range(len(filtered_words) - 1):
        combo = f"{filtered_words[i]} {filtered_words[i+1]}"
        log_info(f"TESTING 2-WORD COMBO: '{combo}'")
        
        # Look for exact matches on this combination
        for player in players_data:
            player_name_normalized = normalize_name(player['name'])
            
            # Check if combo exactly matches full name
            if player_name_normalized == combo:
                log_info(f"EXACT COMBO MATCH: '{combo}' → {player['name']} ({player['team']})")
                combination_matches.append(player)
                continue
            
            # Check if combo is contained in player name
            if combo in player_name_normalized:
                log_info(f"CONTAINED COMBO MATCH: '{combo}' → {player['name']} ({player['team']})")
                combination_matches.append(player)
    
    # Test 3-word combinations
    for i in range(len(filtered_words) - 2):
        combo = f"{filtered_words[i]} {filtered_words[i+1]} {filtered_words[i+2]}"
        log_info(f"TESTING 3-WORD COMBO: '{combo}'")
        
        # Look for exact matches on this combination
        for player in players_data:
            player_name_normalized = normalize_name(player['name'])
            
            # Check if combo exactly matches full name
            if player_name_normalized == combo:
                log_info(f"EXACT 3-WORD COMBO MATCH: '{combo}' → {player['name']} ({player['team']})")
                combination_matches.append(player)
                continue
            
            # Check if combo is contained in player name
            if combo in player_name_normalized:
                log_info(f"CONTAINED 3-WORD COMBO MATCH: '{combo}' → {player['name']} ({player['team']})")
                combination_matches.append(player)
    
    # If we found combination matches, prioritize those
    if combination_matches:
        log_info(f"COMBINATION MATCHES: Found {len(combination_matches)} matches from combinations")
        
        # Deduplicate combination matches
        seen_players = set()
        unique_combo_matches = []
        for player in combination_matches:
            player_key = f"{normalize_name(player['name'])}|{normalize_name(player['team'])}"
            if player_key not in seen_players:
                unique_combo_matches.append(player)
                seen_players.add(player_key)
                log_info(f"UNIQUE COMBO MATCH: Added {player['name']} ({player['team']})")
        
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        asyncio.create_task(log_analytics("Player Search",
            question=text, duration_ms=duration_ms, players_checked=len(players_data),
            matches_found=len(unique_combo_matches), players_found=unique_combo_matches, search_type="combination_match"
        ))
        return unique_combo_matches
    
    # 🔧 STEP 2: Only test individual words if NO combinations matched
    log_info(f"COMBINATION MATCHING: No combination matches found, testing individual words")
    
    individual_matches = []
    
    for word in filtered_words:
        log_info(f"TESTING INDIVIDUAL WORD: '{word}'")
        
        # STRICTER individual word matching - only exact part matches
        word_matches = []
        for player in players_data:
            player_name_normalized = normalize_name(player['name'])
            
            # Check if word exactly matches any part of the name (whole words only)
            name_parts = player_name_normalized.split()
            if word in name_parts:
                log_info(f"EXACT PART MATCH: '{word}' → {player['name']} ({player['team']})")
                word_matches.append(player)
        
        # 🔧 VALIDATION: Only accept individual word matches if they seem reasonable
        if word_matches:
            # For single-word matches, require additional validation
            if len(word_matches) > 10:  # Too many matches = probably a common word
                log_info(f"INDIVIDUAL WORD REJECTED: '{word}' matched {len(word_matches)} players (too many)")
                continue
            
            # Add validated word matches
            individual_matches.extend(word_matches)
    
    # Deduplicate individual matches
    if individual_matches:
        seen_players = set()
        unique_individual_matches = []
        for player in individual_matches:
            player_key = f"{normalize_name(player['name'])}|{normalize_name(player['team'])}"
            if player_key not in seen_players:
                unique_individual_matches.append(player)
                seen_players.add(player_key)
                log_info(f"UNIQUE INDIVIDUAL MATCH: Added {player['name']} ({player['team']})")
        
        log_info(f"INDIVIDUAL MATCHING: Found {len(unique_individual_matches)} total matches from individual words")
        
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        asyncio.create_task(log_analytics("Player Search",
            question=text, duration_ms=duration_ms, players_checked=len(players_data),
            matches_found=len(unique_individual_matches), players_found=unique_individual_matches, search_type="individual_word_match"
        ))
        return unique_individual_matches
    
    log_info(f"INDIVIDUAL WORDS: No matches found from individual words, testing full text as fallback")
    
    # 🔧 STEP 3: FALLBACK - Full text matching (your original logic)
    
    # STEP 3A: Look for EXACT MATCHES on full text
    exact_matches = []
    for player in players_data:
        player_name_normalized = normalize_name(player['name'])
        if player_name_normalized == text_normalized:
            log_info(f"EXACT FULL TEXT MATCH: '{text_normalized}' → {player['name']} ({player['team']})")
            exact_matches.append(player)
    
    # If we found exact matches, return ONLY those
    if exact_matches:
        log_info(f"EXACT FULL TEXT MATCHES: Found {len(exact_matches)} exact matches")
        
        # Deduplicate exact matches
        seen_players = set()
        unique_exact = []
        for player in exact_matches:
            player_key = f"{normalize_name(player['name'])}|{normalize_name(player['team'])}"
            if player_key not in seen_players:
                unique_exact.append(player)
                seen_players.add(player_key)
                log_info(f"EXACT UNIQUE: Added {player['name']} ({player['team']})")
        
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        asyncio.create_task(log_analytics("Player Search",
            question=text, duration_ms=duration_ms, players_checked=len(players_data),
            matches_found=len(unique_exact), players_found=unique_exact, search_type="exact_full_text"
        ))
        return unique_exact
    
    # STEP 3B: Other direct matches on full text
    other_matches = []
    for player in players_data:
        player_name_normalized = normalize_name(player['name'])
        
        # Substring matches
        name_contains_query = text_normalized in player_name_normalized
        query_contains_name = player_name_normalized in text_normalized
        
        # Only allow meaningful substring matches
        is_meaningful_substring = False
        if name_contains_query or query_contains_name:
            query_words = text_normalized.split()
            player_words = player_name_normalized.split()
            
            # Meaningful if query has multiple words OR matches complete word
            if len(query_words) > 1:
                is_meaningful_substring = True
            elif len(query_words) == 1 and query_words[0] in player_words:
                is_meaningful_substring = True
        
        if is_meaningful_substring:
            log_info(f"SUBSTRING MATCH: '{text_normalized}' → {player['name']} ({player['team']})")
            other_matches.append(player)
            continue
        
        # Lastname matching (only for single-word queries)
        query_words = text_normalized.split()
        if len(query_words) == 1:
            name_parts = player_name_normalized.split()
            if len(name_parts) >= 2:
                lastname = name_parts[-1]
                lastname_pattern = f"\\b{re.escape(lastname)}\\b"
                lastname_match = bool(re.search(lastname_pattern, text_normalized))
                
                if lastname_match:
                    log_info(f"LASTNAME MATCH: '{text_normalized}' → {player['name']} ({player['team']})")
                    other_matches.append(player)
    
    # If we found other direct matches, return those
    if other_matches:
        log_info(f"OTHER FULL TEXT MATCHES: Found {len(other_matches)} non-exact direct matches")
        
        # Deduplicate other matches
        seen_players = set()
        unique_other = []
        for player in other_matches:
            player_key = f"{normalize_name(player['name'])}|{normalize_name(player['team'])}"
            if player_key not in seen_players:
                unique_other.append(player)
                seen_players.add(player_key)
                log_info(f"OTHER UNIQUE: Added {player['name']} ({player['team']})")
        
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        asyncio.create_task(log_analytics("Player Search",
            question=text, duration_ms=duration_ms, players_checked=len(players_data),
            matches_found=len(unique_other), players_found=unique_other, search_type="full_text_substring"
        ))
        return unique_other
    
    log_info(f"FULL TEXT MATCHING: No direct matches found, falling back to fuzzy matching")
    
    # STEP 4: Fuzzy matching as final fallback
    matches = fuzzy_match_players(text, max_results=5)
    duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    
    if matches:
        asyncio.create_task(log_analytics("Player Search",
            question=text, duration_ms=duration_ms, players_checked=len(players_data),
            matches_found=len(matches), players_found=matches, search_type="fuzzy_match"
        ))
        return matches
    
    # Log failed search
    asyncio.create_task(log_analytics("Player Search",
        question=text, duration_ms=duration_ms, players_checked=len(players_data),
        matches_found=0, search_type="no_match"
    ))
    return None