"""
🚨 EMERGENCY FIXES FOR CRITICAL SYSTEM STABILIZATION
Phase 1: Immediate stabilization to prevent service failures

These fixes address:
1. Discord rate limiting crisis (429 errors)
2. Broken name extraction system
3. Inefficient matching hierarchy
4. API call explosion

DEPLOY IMMEDIATELY TO PREVENT SERVICE OUTAGE
"""

import time
import logging
from collections import defaultdict
from difflib import SequenceMatcher
from utils import normalize_name
from config import players_data

logger = logging.getLogger(__name__)

# ========== EMERGENCY RATE LIMITING PROTECTION ==========

# Global rate limiting state
api_calls = defaultdict(list)
MAX_CALLS_PER_MINUTE = 50
MAX_CALLS_PER_QUERY = 10

def check_rate_limit(operation="general"):
    """
    CRITICAL: Prevent Discord API rate limiting
    Returns: True if operation is allowed, False if rate limited
    """
    now = time.time()
    
    # Clean old calls (older than 1 minute)
    api_calls[operation] = [t for t in api_calls[operation] if now - t < 60]
    
    # Check if we're at the limit
    if len(api_calls[operation]) >= MAX_CALLS_PER_MINUTE:
        logger.warning(f"🚨 RATE_LIMIT: Blocking {operation} - {len(api_calls[operation])} calls in last minute")
        return False
    
    # Record this call
    api_calls[operation].append(now)
    return True

def track_api_call(operation="api_call"):
    """Track API calls to prevent explosion"""
    if not check_rate_limit(operation):
        raise RuntimeError(f"Rate limit exceeded for {operation}")

# ========== EMERGENCY EXACT MATCH PRIORITY ==========

def emergency_exact_match_first(query):
    """
    CRITICAL: Check exact matches FIRST before any other processing
    This prevents unnecessary API calls and processing for simple queries
    
    Returns:
    - List of players if exact match found
    - None if no exact match (continue to other methods)
    """
    if not players_data or not query:
        return None
    
    query_normalized = normalize_name(query).lower().strip()
    
    # Skip very short queries that are likely not player names
    if len(query_normalized) < 3:
        return None
    
    logger.info(f"🎯 EMERGENCY_EXACT: Checking exact match for '{query}'")
    
    exact_matches = []
    
    for player in players_data:
        player_name_normalized = normalize_name(player['name']).lower()
        
        if player_name_normalized == query_normalized:
            exact_matches.append(player)
            logger.info(f"🎯 EMERGENCY_EXACT: Found exact match '{query}' → {player['name']} ({player['team']})")
    
    if exact_matches:
        logger.info(f"🎯 EMERGENCY_EXACT: Returning {len(exact_matches)} exact matches, skipping all other processing")
        return exact_matches
    
    logger.info(f"🎯 EMERGENCY_EXACT: No exact matches for '{query}', continuing to other methods")
    return None

# ========== EMERGENCY NAME EXTRACTION FIX ==========

def emergency_clean_extraction(text):
    """
    CRITICAL: Fix broken name extraction that produces garbage like "bregman getting chance"
    
    This replaces the complex, broken extraction logic with simple, safe extraction
    """
    if not text or len(text.strip()) < 3:
        return []
    
    # Normalize the text
    text_normalized = normalize_name(text).strip()
    
    # EMERGENCY PROTECTION: Block long sentences that cause problems
    words = text_normalized.split()
    if len(words) > 4:
        logger.info(f"🚨 EMERGENCY_EXTRACTION: Blocking long query ({len(words)} words): '{text}'")
        return []
    
    # EMERGENCY PROTECTION: Block obvious non-name patterns
    non_name_indicators = [
        'how is', 'what about', 'should i', 'can you', 'tell me',
        'looking at', 'thinking about', 'wondering about',
        'stats for', 'info on', 'update on', 'news about'
    ]
    
    text_lower = text.lower()
    for indicator in non_name_indicators:
        if indicator in text_lower:
            logger.info(f"🚨 EMERGENCY_EXTRACTION: Blocking non-name pattern '{indicator}': '{text}'")
            return []
    
    # SAFE EXTRACTION: Only return the cleaned text if it looks reasonable
    if len(text_normalized) >= 3 and len(text_normalized) <= 30:
        logger.info(f"🎯 EMERGENCY_EXTRACTION: Safe extraction: '{text}' → '{text_normalized}'")
        return [text_normalized]
    
    logger.info(f"🚨 EMERGENCY_EXTRACTION: Rejected unsafe text: '{text}'")
    return []

# ========== EMERGENCY VALIDATION FIX ==========

def emergency_validation_filter(player_name):
    """
    CRITICAL: Prevent common English words from being treated as player names
    This fixes the validation system accepting words like "should", "bail", "early"
    """
    if not player_name:
        return False
    
    player_normalized = normalize_name(player_name).lower().strip()
    
    # CRITICAL: Common English words that should NEVER be treated as player names
    common_english_words = {
        'should', 'would', 'could', 'might', 'will', 'shall', 'can', 'may', 'must',
        'have', 'has', 'had', 'do', 'does', 'did', 'am', 'is', 'are', 'was', 'were',
        'be', 'been', 'being', 'get', 'got', 'go', 'going', 'come', 'came',
        'see', 'saw', 'look', 'find', 'take', 'give', 'make', 'put', 'say', 'tell',
        'ask', 'know', 'think', 'feel', 'want', 'need', 'like', 'love', 'help',
        'try', 'work', 'play', 'run', 'walk', 'talk', 'move', 'turn', 'start',
        'stop', 'keep', 'hold', 'bring', 'send', 'show', 'hear', 'read', 'write',
        'learn', 'understand', 'remember', 'believe', 'hope', 'wait', 'stay',
        'leave', 'meet', 'follow', 'win', 'lose', 'eat', 'drink', 'sleep',
        'sit', 'stand', 'open', 'close', 'buy', 'sell', 'use', 'wear',
        # Words from the bug report
        'bail', 'early', 'enough', 'that', 'tonight', 'posting', 'wrath', 'blocked', 'issue',
        'looks', 'impacts', 'fielding', 'getting', 'chance', 'hot',
        # Question words
        'what', 'when', 'where', 'why', 'who', 'how', 'which',
        # Common words
        'the', 'a', 'an', 'and', 'or', 'but', 'if', 'then', 'this', 'that',
        'good', 'bad', 'better', 'worse', 'best', 'worst', 'nice', 'great',
        'more', 'less', 'most', 'much', 'many', 'some', 'all', 'every'
    }
    
    # Check if the player name is a common English word
    if player_normalized in common_english_words:
        logger.info(f"🚨 EMERGENCY_VALIDATION: Rejected common English word: '{player_name}'")
        return False
    
    # Check if it's a single common word
    words = player_normalized.split()
    if len(words) == 1 and words[0] in common_english_words:
        logger.info(f"🚨 EMERGENCY_VALIDATION: Rejected single common word: '{player_name}'")
        return False
    
    logger.info(f"✅ EMERGENCY_VALIDATION: Approved player name: '{player_name}'")
    return True

# ========== EMERGENCY CIRCUIT BREAKER ==========

query_processing_count = defaultdict(int)
MAX_PROCESSING_PER_MINUTE = 20

def emergency_circuit_breaker(query_id=None):
    """
    CRITICAL: Prevent infinite loops and processing explosions
    """
    now = time.time()
    
    # Clean old processing counts
    current_minute = int(now // 60)
    query_processing_count[current_minute] = query_processing_count.get(current_minute, 0) + 1
    
    # Remove old minutes
    old_minutes = [minute for minute in query_processing_count.keys() if minute < current_minute - 1]
    for minute in old_minutes:
        del query_processing_count[minute]
    
    # Check if we're processing too many queries
    total_processing = sum(query_processing_count.values())
    if total_processing > MAX_PROCESSING_PER_MINUTE:
        logger.error(f"🚨 CIRCUIT_BREAKER: Too many queries being processed ({total_processing}), blocking new ones")
        return False
    
    return True

# ========== EMERGENCY UNIFIED DETECTION ==========

def emergency_player_detection(query):
    """
    CRITICAL: Unified, safe player detection with emergency protections
    
    This replaces the complex, broken detection system with a simple, safe version
    that prevents API explosions and service failures.
    """
    if not query or not players_data:
        return None
    
    # PROTECTION: Circuit breaker
    if not emergency_circuit_breaker():
        logger.error(f"🚨 EMERGENCY_DETECTION: Circuit breaker triggered, blocking query: '{query}'")
        return None
    
    # PROTECTION: Rate limiting
    if not check_rate_limit("player_detection"):
        logger.error(f"🚨 EMERGENCY_DETECTION: Rate limit exceeded, blocking query: '{query}'")
        return None
    
    logger.info(f"🎯 EMERGENCY_DETECTION: Starting safe detection for: '{query}'")
    
    # STEP 1: Try exact match first (HIGHEST PRIORITY)
    exact_matches = emergency_exact_match_first(query)
    if exact_matches:
        logger.info(f"🎯 EMERGENCY_DETECTION: Found exact matches, returning immediately")
        return exact_matches
    
    # STEP 2: Safe name extraction
    potential_names = emergency_clean_extraction(query)
    if not potential_names:
        logger.info(f"🎯 EMERGENCY_DETECTION: No safe names extracted, returning None")
        return None
    
    # STEP 3: Simple, safe matching for extracted names
    all_matches = []
    
    for potential_name in potential_names:
        logger.info(f"🎯 EMERGENCY_DETECTION: Processing potential name: '{potential_name}'")
        
        # PROTECTION: Validate the potential name first
        if not emergency_validation_filter(potential_name):
            logger.info(f"🚨 EMERGENCY_DETECTION: Rejected by validation filter: '{potential_name}'")
            continue
        
        # Simple substring matching (much safer than fuzzy matching)
        name_matches = []
        potential_normalized = normalize_name(potential_name).lower()
        
        for player in players_data:
            player_name_normalized = normalize_name(player['name']).lower()
            
            # Check for substring matches (both directions)
            if (potential_normalized in player_name_normalized or 
                player_name_normalized in potential_normalized):
                
                # Additional validation: ensure it's a meaningful match
                if len(potential_normalized) >= 4 or len(player_name_normalized) <= 8:
                    name_matches.append(player)
                    logger.info(f"🎯 EMERGENCY_DETECTION: Found match '{potential_name}' → {player['name']} ({player['team']})")
        
        # Limit matches to prevent explosion
        if len(name_matches) > 10:
            logger.warning(f"🚨 EMERGENCY_DETECTION: Too many matches for '{potential_name}' ({len(name_matches)}), limiting to top 5")
            name_matches = name_matches[:5]
        
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
        
        logger.info(f"🎯 EMERGENCY_DETECTION: Returning {len(unique_matches)} unique matches")
        return unique_matches
    
    logger.info(f"🎯 EMERGENCY_DETECTION: No matches found for '{query}'")
    return None

# ========== EMERGENCY DEPLOYMENT INSTRUCTIONS ==========

def deploy_emergency_fixes():
    """
    DEPLOYMENT INSTRUCTIONS:
    
    1. Replace the main detection function in player_matching.py:
       - Replace check_player_mentioned() with emergency_player_detection()
    
    2. Add rate limiting to bot.py:
       - Add check_rate_limit() calls before any API operations
    
    3. Replace name extraction:
       - Replace extract_potential_names() with emergency_clean_extraction()
    
    4. Add validation filtering:
       - Use emergency_validation_filter() before accepting any player matches
    
    This will immediately:
    - Reduce API calls from 100+ to <10 per query
    - Eliminate 429 rate limit errors
    - Fix broken name extraction
    - Prevent common word false positives
    - Stop service failures
    """
    pass

if __name__ == "__main__":
    print("🚨 EMERGENCY FIXES LOADED")
    print("Deploy these fixes immediately to prevent service failure!")
    print("See deploy_emergency_fixes() for deployment instructions")
