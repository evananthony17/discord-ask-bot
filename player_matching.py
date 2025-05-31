import re
import asyncio
from datetime import datetime
from difflib import SequenceMatcher
from config import players_data
from utils import normalize_name, expand_nicknames, is_likely_player_request
from logging_system import log_analytics

# -------- NAME EXTRACTION --------

def extract_potential_names(text):
    """ENHANCED: Extract potential player names with multi-player detection"""
    # First expand nicknames
    expanded_text = expand_nicknames(text)
    if expanded_text != text:
        print(f"NAME EXTRACTION: Expanded '{text}' to '{expanded_text}'")
        text = expanded_text
    
    text_normalized = normalize_name(text)
    potential_names = []
    
    # ENHANCED: Split text by common separators for multi-player detection
    # Split by "and", "&", "vs", "versus", commas, etc.
    segments = re.split(r'\s+(?:and|&|vs\.?|versus|,)\s+', text_normalized, flags=re.IGNORECASE)
    
    if len(segments) > 1:
        print(f"MULTI-PLAYER: Split '{text}' into {len(segments)} segments: {segments}")
        
        # Process each segment individually
        for i, segment in enumerate(segments):
            segment = segment.strip()
            if len(segment) >= 3:  # Reasonable minimum length
                potential_names.append(segment)
                print(f"MULTI-PLAYER: Segment {i+1}: '{segment}'")
    
    # Remove common question words and phrases
    stop_words = {
        'how', 'is', 'was', 'are', 'were', 'doing', 'playing', 'performed', 
        'the', 'a', 'an', 'about', 'what', 'when', 'where', 'why', 'who',
        'should', 'would', 'could', 'can', 'will', 'today', 'yesterday', 
        'tomorrow', 'this', 'that', 'these', 'those', 'season', 'year', 
        'game', 'games', 'update', 'on', 'for', 'with', 'any', 'get', 'stats',
        'more', 'like', 'than', 'then', 'just', 'only', 'also', 'even',
        'much', 'many', 'some', 'all', 'most', 'best', 'worst', 'better', 'worse',
        # ENHANCED: Add common words that match player names
        'has', 'have', 'had', 'his', 'her', 'him', 'them', 'they', 'their',
        'been', 'being', 'be', 'am', 'as', 'at', 'an', 'or', 'if', 'it',
        'up', 'out', 'in', 'to', 'of', 'my', 'me', 'we', 'us', 'you', 'your'
    }
    
    # ENHANCED: Add minimum length requirement for individual words
    min_word_length = 4  # "has" (3 chars) won't match anymore
    
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
    
    # ENHANCED: Only add individual words if they're reasonably long and look name-like
    non_name_words = {
        'stats', 'news', 'info', 'question', 'playing', 'game', 'season', 'year', 'team',
        'downdate', 'upgrade', 'downgrade', 'update', 'like', 'more', 'less', 'better', 'worse',
        'good', 'bad', 'nice', 'cool', 'awesome', 'great', 'terrible', 'amazing', 'fantastic',
        'horrible', 'perfect', 'awful', 'wonderful', 'excellent', 'outstanding', 'impressive',
        'doing', 'going', 'coming', 'looking', 'getting', 'having', 'being', 'seeing',
        'thinking', 'feeling', 'knowing', 'saying', 'telling', 'asking', 'giving', 'taking'
    }
    
    for word in filtered_words:
        if (len(word) >= min_word_length and 
            word not in non_name_words and 
            not word.isdigit() and  # No pure numbers
            word.isalpha()):  # Only alphabetic characters
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
    
    print(f"NAME EXTRACTION: Found {len(unique_names)} potential names from '{text}': {unique_names}")
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
        print(f"🎯 LAST NAME MATCH: '{potential_name}' vs last name '{player_last_name}' = {similarity:.3f}")
        return similarity, True
    
    return None, False

# -------- FUZZY MATCHING --------

def fuzzy_match_players(text, max_results=8):
    """FIXED: Fuzzy match player names and return ALL matches above threshold"""
    from logging_system import log_info
    
    print(f"🔍 FUZZY MATCH: Starting for '{text}'")
    asyncio.create_task(log_info(f"FUZZY MATCH Starting", f"Query: '{text}'"))
    
    if not players_data:
        print("🔍 FUZZY MATCH: No players data available")
        return []
    
    # Extract potential player names from the text
    potential_names = extract_potential_names(text)
    matches = []
    
    print(f"🔍 FUZZY MATCH: Testing {len(potential_names)} potential names: {potential_names}")
    asyncio.create_task(log_info(f"FUZZY MATCH Potential Names", f"Found {len(potential_names)} names: {potential_names}"))
    
    # Try fuzzy matching with each potential name
    for potential_name in potential_names:
        print(f"🔍 FUZZY MATCH: Testing potential name: '{potential_name}'")
        asyncio.create_task(log_info(f"FUZZY MATCH Testing", f"Name: '{potential_name}'"))
        
        for i, player in enumerate(players_data):
            player_name = normalize_name(player['name'])
            
            # First check for special last name match
            lastname_sim, is_lastname_match = check_last_name_match(potential_name, player_name)
            
            if is_lastname_match and lastname_sim >= 0.75:
                print(f"✅ LAST NAME MATCH: '{potential_name}' → {player['name']} ({player['team']}) = {lastname_sim:.3f}")
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
                print(f"✅ FUZZY MATCH: '{potential_name}' → {player['name']} ({player['team']}) = {best_similarity:.3f} (threshold: {threshold})")
                asyncio.create_task(log_info(f"FUZZY MATCH Found", f"'{potential_name}' → {player['name']} ({player['team']}) = {best_similarity:.3f}"))
                matches.append((player, best_similarity))
            elif best_similarity >= 0.5:  # Log near misses for debugging
                print(f"❌ NEAR MISS: '{potential_name}' → {player['name']} ({player['team']}) = {best_similarity:.3f} (needed: {threshold})")
                # Only log Acuña near misses to avoid spam
                if 'acuna' in normalize_name(player['name']).lower():
                    asyncio.create_task(log_info(f"ACUÑA NEAR MISS", f"'{potential_name}' → {player['name']} ({player['team']}) = {best_similarity:.3f} (needed: {threshold})"))
    
    print(f"🔍 FUZZY MATCH: Found {len(matches)} total matches before deduplication")
    asyncio.create_task(log_info(f"FUZZY MATCH Total", f"Found {len(matches)} matches before deduplication"))
    
    # Sort by score and remove duplicates
    matches.sort(key=lambda x: x[1], reverse=True)
    seen_players = set()
    unique_matches = []
    
    for player, score in matches:
        player_key = f"{normalize_name(player['name'])}|{normalize_name(player['team'])}"
        if player_key not in seen_players and len(unique_matches) < max_results:
            print(f"✅ ADDING MATCH: {player['name']} ({player['team']}) = {score:.3f}")
            asyncio.create_task(log_info(f"FUZZY MATCH Adding", f"{player['name']} ({player['team']}) = {score:.3f}"))
            unique_matches.append(player)
            seen_players.add(player_key)
        else:
            if player_key in seen_players:
                print(f"🔄 DUPLICATE SKIPPED: {player['name']} ({player['team']})")
            else:
                print(f"📊 MAX RESULTS REACHED: Skipping {player['name']} ({player['team']})")
    
    print(f"🔍 FUZZY MATCH: Returning {len(unique_matches)} unique matches")
    asyncio.create_task(log_info(f"FUZZY MATCH Final", f"Returning {len(unique_matches)} unique matches: {[p['name'] for p in unique_matches]}"))
    return unique_matches

# -------- MAIN PLAYER CHECKING FUNCTION --------

def check_player_mentioned(text):
    """Check if any player is mentioned using improved fuzzy matching"""
    start_time = datetime.now()
    
    print(f"🔍 CHECK PLAYER: Looking for players in '{text}'")
    
    if not players_data or not is_likely_player_request(text):
        return None
    
    # First, expand any nicknames
    expanded_text = expand_nicknames(text)
    if expanded_text != text:
        print(f"🏷️ NICKNAME: Using expanded text: '{expanded_text}'")
        text = expanded_text
    
    # Direct matches first
    text_normalized = normalize_name(text)
    direct_matches = []
    for player in players_data:
        player_name_normalized = normalize_name(player['name'])
        if (player_name_normalized in text_normalized or 
            text_normalized in player_name_normalized or
            player_name_normalized == text_normalized):
            direct_matches.append(player)
    
    # Deduplicate direct matches
    if direct_matches:
        seen_players = set()
        unique_direct = []
        for player in direct_matches:
            player_key = f"{normalize_name(player['name'])}|{normalize_name(player['team'])}"
            if player_key not in seen_players:
                unique_direct.append(player)
                seen_players.add(player_key)
        
        if unique_direct:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            asyncio.create_task(log_analytics("Player Search",
                question=text, duration_ms=duration_ms, players_checked=len(players_data),
                matches_found=len(unique_direct), players_found=unique_direct, search_type="direct_match"
            ))
            return unique_direct
    
    # Fuzzy matching
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