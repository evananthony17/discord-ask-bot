import re
from difflib import SequenceMatcher
from config import players_data
from utils import normalize_name
from logging_system import log_info

# Context types for validation
CONTEXT_USER_QUESTION = "user_question"
CONTEXT_EXPERT_REPLY = "expert_reply"
CONTEXT_METADATA = "metadata"
CONTEXT_UNKNOWN = "unknown"

def detect_validation_context(text):
    """
    Detect the context of the text to apply appropriate validation rules
    Returns: context type (user_question, expert_reply, metadata, unknown)
    """
    text_lower = text.lower()
    
    # Expert reply indicators
    expert_indicators = [
        'replied:', 'answered:', 'response:', 'expert',
        'in my opinion', 'i think', 'i believe', 'i would say',
        'based on', 'according to', 'from what i see',
        'looking at', 'considering', 'given that'
    ]
    
    # Metadata indicators
    metadata_indicators = [
        '[players:', '[player:', 'players:', 'player:',
        'team:', 'position:', 'stats:'
    ]
    
    # User question indicators
    question_indicators = [
        'asked:', 'question:', '?', 'how is', 'what about',
        'should i', 'can you', 'tell me about'
    ]
    
    # Check for metadata context first (highest priority)
    if any(indicator in text_lower for indicator in metadata_indicators):
        return CONTEXT_METADATA
    
    # Check for expert reply context
    if any(indicator in text_lower for indicator in expert_indicators):
        return CONTEXT_EXPERT_REPLY
    
    # Check for user question context
    if '?' in text:
        return CONTEXT_USER_QUESTION

    # Check for other question indicators
    if any(indicator in text_lower for indicator in question_indicators):
        return CONTEXT_USER_QUESTION

    # For short texts (likely user questions), default to user question context
    if len(text.split()) <= 15:
        return CONTEXT_USER_QUESTION
    
    # Default to unknown context (will use moderate validation)
    return CONTEXT_UNKNOWN

def is_valid_player_name_phrase(phrase, matched_player_name, context=CONTEXT_UNKNOWN):
    """
    Context-aware validation of player name phrases
    - Strict validation for user questions (prevents false positives)
    - Relaxed validation for expert replies (allows natural language)
    - Minimal validation for metadata (basic structure only)
    """
    phrase_normalized = normalize_name(phrase).lower()
    player_normalized = normalize_name(matched_player_name).lower()
    
    # Split into words
    phrase_words = phrase_normalized.split()
    player_words = player_normalized.split()
    
    log_info(f"VALIDATING: '{phrase}' → '{matched_player_name}' (context: {context})")
    log_info(f"PHRASE WORDS: {phrase_words}")
    log_info(f"PLAYER WORDS: {player_words}")
    
    # Apply context-specific validation rules
    if context == CONTEXT_METADATA:
        # Minimal validation for metadata - just basic structure
        return validate_metadata_context(phrase_words, player_words, phrase, matched_player_name)
    elif context == CONTEXT_EXPERT_REPLY:
        # Relaxed validation for expert replies
        return validate_expert_reply_context(phrase_words, player_words, phrase, matched_player_name, phrase_normalized, player_normalized)
    else:
        # Strict validation for user questions and unknown context
        return validate_user_question_context(phrase_words, player_words, phrase, matched_player_name, phrase_normalized, player_normalized)

def validate_metadata_context(phrase_words, player_words, phrase, matched_player_name):
    """Minimal validation for metadata context"""
    # For metadata, just check basic structure
    if len(phrase_words) >= 1:
        # At least one word should be reasonable length
        if any(len(word) >= 2 for word in phrase_words):
            log_info(f"METADATA VALIDATION PASSED: '{phrase}' → '{matched_player_name}'")
            return True
    
    log_info(f"METADATA VALIDATION FAILED: '{phrase}' → '{matched_player_name}' - insufficient structure")
    return False

def validate_expert_reply_context(phrase_words, player_words, phrase, matched_player_name, phrase_normalized, player_normalized):
    """Relaxed validation for expert replies"""
    # Rule 1: Only reject the most obvious non-name patterns (much more permissive)
    critical_non_name_patterns = [
        # Only the most obvious false positives
        r'\bmore like\b', r'\bless like\b', r'\bmuch like\b',
        r'\bhow about\b', r'\bwhat about\b',
        r'\bkind of\b', r'\bsort of\b', r'\btype of\b',
        r'\bout of\b', r'\binstead of\b'
    ]
    
    for pattern in critical_non_name_patterns:
        if re.search(pattern, phrase_normalized):
            log_info(f"EXPERT REPLY VALIDATION FAILED: Phrase '{phrase}' matches critical non-name pattern: {pattern}")
            return False
    
    # Rule 2: More lenient word length requirements
    if len(phrase_words) == 2:
        word1, word2 = phrase_words
        if len(word1) < 2 or len(word2) < 2:
            log_info(f"EXPERT REPLY VALIDATION FAILED: Words too short: {word1}, {word2}")
            return False
    
    # Rule 3: Use same permissive logic as user questions for consistency
    similarity = SequenceMatcher(None, phrase_normalized, player_normalized).ratio()
    
    if len(phrase_words) >= 2:
        # Check if at least one actual player name part is in the phrase
        player_name_in_phrase = any(
            player_word in phrase_words 
            for player_word in player_words 
            if len(player_word) >= 3  # Only consider meaningful name parts
        )
        
        if player_name_in_phrase:
            # If we found actual name parts, be very permissive with similarity (same as user questions)
            min_similarity = 0.2
            log_info(f"Found player name part in phrase - using permissive threshold: {min_similarity}")
        else:
            # If no name parts found, use moderate threshold for expert replies (more lenient than user questions)
            min_similarity = 0.3
            log_info(f"No player name parts found - using moderate threshold: {min_similarity}")
        
        if similarity < min_similarity:
            log_info(f"EXPERT REPLY VALIDATION FAILED: Low similarity {similarity:.3f} for multi-word phrase (required: {min_similarity})")
            return False
        else:
            log_info(f"Similarity check passed: {similarity:.3f} >= {min_similarity}")
    
    # Rule 4: More lenient word matching (same as user questions)
    if len(phrase_words) >= 2:
        phrase_words_in_player = sum(1 for word in phrase_words if word in player_words)
        if phrase_words_in_player == 0:
            log_info(f"EXPERT REPLY VALIDATION FAILED: No phrase words found in player name")
            return False
    
    log_info(f"EXPERT REPLY VALIDATION PASSED: '{phrase}' → '{matched_player_name}'")
    return True

def validate_user_question_context(phrase_words, player_words, phrase, matched_player_name, phrase_normalized, player_normalized):
    """PERMISSIVE validation for user questions - simplified to reduce false negatives"""
    
    # 🔧 PERMISSIVE: Only reject the most obvious non-name patterns
    # Removed most pattern checks to be more permissive
    critical_non_name_patterns = [
        r'\bhow do\b', r'\bwhat do\b', r'\bhow can\b', r'\bwhat can\b',
        r'\bhow will\b', r'\bwhat will\b', r'\bhow should\b', r'\bwhat should\b',
        r'\bmax projection\b', r'\bmin projection\b', r'\bbest case\b', r'\bworst case\b',
    ]
    
    for pattern in critical_non_name_patterns:
        if re.search(pattern, phrase_normalized):
            log_info(f"PERMISSIVE VALIDATION FAILED: Phrase '{phrase}' matches critical non-name pattern: {pattern}")
            return False
    
    # 🔧 PERMISSIVE: Much more lenient word length requirements
    if len(phrase_words) == 2:
        word1, word2 = phrase_words
        if len(word1) < 2 or len(word2) < 2:
            log_info(f"PERMISSIVE VALIDATION FAILED: Words too short: {word1}, {word2}")
            return False
        
        # 🔧 PERMISSIVE: Only reject the most obvious non-name combos
        critical_non_name_combos = {
            ('how', 'do'), ('what', 'do'), ('how', 'can'), ('what', 'can'),
            ('how', 'will'), ('what', 'will'), ('how', 'should'), ('what', 'should'),
            ('max', 'projection'), ('min', 'projection'), ('best', 'case'), ('worst', 'case'),
        }
        
        if (word1, word2) in critical_non_name_combos:
            log_info(f"PERMISSIVE VALIDATION FAILED: Critical non-name combo detected: {word1}, {word2}")
            return False
    
    # 🔧 PERMISSIVE: Much lower similarity thresholds
    similarity = SequenceMatcher(None, phrase_normalized, player_normalized).ratio()
    
    if len(phrase_words) >= 2:
        # Check if at least one actual player name part is in the phrase
        player_name_in_phrase = any(
            player_word in phrase_words 
            for player_word in player_words 
            if len(player_word) >= 3  # Only consider meaningful name parts
        )
        
        if player_name_in_phrase:
            # If we found actual name parts, be very permissive with similarity
            min_similarity = 0.1  # Very low threshold
            log_info(f"Found player name part in phrase - using very permissive threshold: {min_similarity}")
        else:
            # If no name parts found, still be more permissive than before
            min_similarity = 0.3  # Lowered from 0.6
            log_info(f"No player name parts found - using moderate threshold: {min_similarity}")
        
        if similarity < min_similarity:
            log_info(f"PERMISSIVE VALIDATION FAILED: Low similarity {similarity:.3f} for multi-word phrase (required: {min_similarity})")
            return False
        else:
            log_info(f"Similarity check passed: {similarity:.3f} >= {min_similarity}")
    
    # 🔧 PERMISSIVE: Remove the phrase words check - too restrictive
    # This was rejecting legitimate matches where the phrase didn't contain exact player name parts
    
    # 🔧 PERMISSIVE: Remove the common non-name words check - too restrictive
    # This was rejecting legitimate matches that happened to contain common words
    
    log_info(f"PERMISSIVE VALIDATION PASSED: '{phrase}' → '{matched_player_name}'")
    return True

def validate_player_mention_in_text(text, player_name, context=None):
    """
    NEW: Validate if a full text/message mentions a specific player
    Use Case: Check if "Paxton Schultz how is he looking" mentions "Paxton Schultz"
    
    Args:
        text: Full message/text to check
        player_name: Specific player name to look for
        context: Optional context hint
    """
    if context is None:
        context = detect_validation_context(text)
    
    log_info(f"MENTION VALIDATION: Checking if '{text}' mentions '{player_name}' (context: {context})")
    
    # 🔧 CRITICAL BUG FIX: Prevent common English words from being validated as player names
    # This was causing words like "should", "bail", "early" to be treated as player names
    
    text_normalized = normalize_name(text).lower()
    player_normalized = normalize_name(player_name).lower()
    
    # 🔧 CRITICAL FIX: Filter out obvious non-player names before any validation
    # Common English words that should never be treated as player names
    common_english_words = {
        'should', 'would', 'could', 'might', 'will', 'shall', 'can', 'may', 'must',
        'have', 'has', 'had', 'haven', 'hasn', 'hadn', 'do', 'does', 'did', 'don', 'doesn', 'didn',
        'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'get', 'got', 'getting', 'go', 'going', 'went', 'gone', 'come', 'coming', 'came',
        'see', 'seeing', 'saw', 'seen', 'look', 'looking', 'looked', 'find', 'finding', 'found',
        'take', 'taking', 'took', 'taken', 'give', 'giving', 'gave', 'given', 'make', 'making', 'made',
        'put', 'putting', 'say', 'saying', 'said', 'tell', 'telling', 'told', 'ask', 'asking', 'asked',
        'know', 'knowing', 'knew', 'known', 'think', 'thinking', 'thought', 'feel', 'feeling', 'felt',
        'want', 'wanting', 'wanted', 'need', 'needing', 'needed', 'like', 'liking', 'liked',
        'love', 'loving', 'loved', 'help', 'helping', 'helped', 'try', 'trying', 'tried',
        'work', 'working', 'worked', 'play', 'playing', 'played', 'run', 'running', 'ran',
        'walk', 'walking', 'walked', 'talk', 'talking', 'talked', 'move', 'moving', 'moved',
        'turn', 'turning', 'turned', 'start', 'starting', 'started', 'stop', 'stopping', 'stopped',
        'end', 'ending', 'ended', 'begin', 'beginning', 'began', 'begun', 'keep', 'keeping', 'kept',
        'hold', 'holding', 'held', 'bring', 'bringing', 'brought', 'carry', 'carrying', 'carried',
        'send', 'sending', 'sent', 'show', 'showing', 'showed', 'shown', 'hear', 'hearing', 'heard',
        'listen', 'listening', 'listened', 'read', 'reading', 'write', 'writing', 'wrote', 'written',
        'learn', 'learning', 'learned', 'teach', 'teaching', 'taught', 'study', 'studying', 'studied',
        'understand', 'understanding', 'understood', 'remember', 'remembering', 'remembered',
        'forget', 'forgetting', 'forgot', 'forgotten', 'believe', 'believing', 'believed',
        'hope', 'hoping', 'hoped', 'wish', 'wishing', 'wished', 'expect', 'expecting', 'expected',
        'wait', 'waiting', 'waited', 'stay', 'staying', 'stayed', 'leave', 'leaving', 'left',
        'arrive', 'arriving', 'arrived', 'return', 'returning', 'returned', 'visit', 'visiting', 'visited',
        'meet', 'meeting', 'met', 'join', 'joining', 'joined', 'follow', 'following', 'followed',
        'lead', 'leading', 'led', 'win', 'winning', 'won', 'lose', 'losing', 'lost',
        'beat', 'beating', 'fight', 'fighting', 'fought', 'kill', 'killing', 'killed',
        'die', 'dying', 'died', 'live', 'living', 'lived', 'eat', 'eating', 'ate', 'eaten',
        'drink', 'drinking', 'drank', 'drunk', 'sleep', 'sleeping', 'slept', 'wake', 'waking', 'woke', 'woken',
        'sit', 'sitting', 'sat', 'stand', 'standing', 'stood', 'lie', 'lying', 'lay', 'lain',
        'fall', 'falling', 'fell', 'fallen', 'rise', 'rising', 'rose', 'risen', 'fly', 'flying', 'flew', 'flown',
        'drive', 'driving', 'drove', 'driven', 'ride', 'riding', 'rode', 'ridden', 'swim', 'swimming', 'swam', 'swum',
        'jump', 'jumping', 'jumped', 'climb', 'climbing', 'climbed', 'throw', 'throwing', 'threw', 'thrown',
        'catch', 'catching', 'caught', 'hit', 'hitting', 'kick', 'kicking', 'kicked',
        'push', 'pushing', 'pushed', 'pull', 'pulling', 'pulled', 'lift', 'lifting', 'lifted',
        'drop', 'dropping', 'dropped', 'pick', 'picking', 'picked', 'choose', 'choosing', 'chose', 'chosen',
        'decide', 'deciding', 'decided', 'change', 'changing', 'changed', 'happen', 'happening', 'happened',
        'become', 'becoming', 'became', 'seem', 'seeming', 'seemed', 'appear', 'appearing', 'appeared',
        'open', 'opening', 'opened', 'close', 'closing', 'closed', 'break', 'breaking', 'broke', 'broken',
        'fix', 'fixing', 'fixed', 'build', 'building', 'built', 'create', 'creating', 'created',
        'destroy', 'destroying', 'destroyed', 'clean', 'cleaning', 'cleaned', 'wash', 'washing', 'washed',
        'cook', 'cooking', 'cooked', 'buy', 'buying', 'bought', 'sell', 'selling', 'sold',
        'pay', 'paying', 'paid', 'cost', 'costing', 'spend', 'spending', 'spent',
        'save', 'saving', 'saved', 'earn', 'earning', 'earned', 'own', 'owning', 'owned',
        'use', 'using', 'used', 'wear', 'wearing', 'wore', 'worn', 'cut', 'cutting',
        # Common words from the bug report
        'bail', 'early', 'enough', 'that', 'tonight', 'posting', 'wrath', 'blocked', 'issue',
        # Question words
        'what', 'when', 'where', 'why', 'who', 'how', 'which', 'whose', 'whom',
        # Pronouns and articles
        'i', 'me', 'my', 'mine', 'we', 'us', 'our', 'ours', 'you', 'your', 'yours',
        'he', 'him', 'his', 'she', 'her', 'hers', 'it', 'its', 'they', 'them', 'their', 'theirs',
        'this', 'that', 'these', 'those', 'the', 'a', 'an',
        # Prepositions and conjunctions
        'and', 'or', 'but', 'if', 'then', 'when', 'where', 'why', 'how', 'because', 'since',
        'to', 'of', 'in', 'on', 'at', 'by', 'for', 'with', 'without', 'about', 'above', 'below',
        'over', 'under', 'up', 'down', 'out', 'off', 'away', 'back', 'here', 'there',
        # Time words
        'now', 'then', 'today', 'tomorrow', 'yesterday', 'always', 'never', 'sometimes',
        'often', 'usually', 'rarely', 'soon', 'late', 'early', 'before', 'after',
        # Quantity words
        'more', 'less', 'most', 'least', 'much', 'many', 'few', 'some', 'any', 'all',
        'every', 'each', 'both', 'either', 'neither', 'one', 'two', 'three', 'first', 'last',
        # Quality words
        'good', 'bad', 'better', 'worse', 'best', 'worst', 'nice', 'great', 'awesome',
        'terrible', 'horrible', 'amazing', 'fantastic', 'perfect', 'awful', 'wonderful',
        'excellent', 'outstanding', 'impressive', 'big', 'small', 'large', 'huge', 'tiny',
        'long', 'short', 'tall', 'high', 'low', 'fast', 'slow', 'quick', 'easy', 'hard',
        'difficult', 'simple', 'complex', 'new', 'old', 'young', 'fresh', 'clean', 'dirty'
    }
    
    # If the player name is a common English word, reject it immediately
    if player_normalized in common_english_words:
        log_info(f"MENTION VALIDATION FAILED: '{player_name}' is a common English word, not a player name")
        return False
    
    # Also check if it's a single common word (for cases like "should" vs "Should Martinez")
    player_words = player_normalized.split()
    if len(player_words) == 1 and player_words[0] in common_english_words:
        log_info(f"MENTION VALIDATION FAILED: '{player_name}' is a single common English word, not a player name")
        return False
    
    # 🔧 CRITICAL FIX: Split text on separators, not just spaces
    # This handles cases like "Soto;Edman;trout" properly
    import re
    text_words = re.split(r'[;\s,&/\(\)\[\]]+', text_normalized)
    text_words = [word for word in text_words if word]  # Remove empty strings
    
    # 🔧 CRITICAL FIX: Enhanced last name matching for compound names like "De La Cruz"
    # Extract the actual last name (last word) from player name
    if player_words:
        actual_last_name = player_words[-1]
        
        # 🔧 ADDITIONAL SAFETY: Don't validate if the "lastname" is a common word
        if actual_last_name in common_english_words:
            log_info(f"MENTION VALIDATION FAILED: Last name '{actual_last_name}' is a common English word")
            return False
        
        # Check if the actual last name appears in the text
        if actual_last_name in text_words:
            log_info(f"MENTION VALIDATION PASSED: '{player_name}' found via last name '{actual_last_name}' in '{text}' (context: {context})")
            return True
        
        # For compound last names like "De La Cruz", also check if any significant part matches
        # Look for compound name patterns (2+ consecutive words that could be a compound last name)
        for i in range(len(player_words) - 1):
            compound_part = player_words[i]
            # Check if this could be part of a compound last name (like "De", "La", "Van", etc.)
            if len(compound_part) >= 2 and compound_part in text_words:
                # Check if the following word is also in the text (like "La" followed by "Cruz")
                if i + 1 < len(player_words):
                    next_part = player_words[i + 1]
                    if next_part in text_words:
                        log_info(f"MENTION VALIDATION PASSED: '{player_name}' found via compound name parts '{compound_part} {next_part}' in '{text}' (context: {context})")
                        return True
    
    # Count how many player name parts appear in the text
    matching_parts = sum(1 for part in player_words if part in text_words)
    
    # For mention validation, if most of the player name appears, it's valid
    if len(player_words) == 1:
        # Single name (like "Rodon") - just check if it appears
        is_valid = player_normalized in text_normalized
    elif len(player_words) == 2:
        # Two-part name - require at least one part to match
        is_valid = matching_parts >= 1
    else:
        # Multi-part name - require at least half the parts
        is_valid = matching_parts >= len(player_words) // 2
    
    if is_valid:
        log_info(f"MENTION VALIDATION PASSED: '{player_name}' found in '{text}' (context: {context})")
    else:
        log_info(f"MENTION VALIDATION FAILED: '{player_name}' not clearly mentioned in '{text}' (context: {context})")
    
    return is_valid

def validate_extracted_player_name(phrase, player_name, context=None):
    """
    ORIGINAL: Validate if an extracted phrase looks like it could be a player name
    Use Case: Check if "rodon" could refer to "Carlos Rodon"
    
    Args:
        phrase: Extracted phrase/word to validate
        player_name: Player name it supposedly matches
        context: Optional context hint
    """
    # This is the original validation logic - keep it unchanged
    return is_valid_player_name_phrase(phrase, player_name, context)

def validate_player_matches(text, matches, context=None):
    """
    UPDATED: Context-aware filtering using the appropriate validation method
    
    Args:
        text: The text being validated
        matches: List of player matches to validate
        context: Optional context hint (user_question, expert_reply, metadata)
    """
    if not matches:
        return matches
    
    # Auto-detect context if not provided
    if context is None:
        context = detect_validation_context(text)
    
    log_info(f"VALIDATION: Processing {len(matches)} matches with context: {context}")
    
    validated_matches = []
    
    for player in matches:
        # Use mention validation (more permissive) for full text validation
        if validate_player_mention_in_text(text, player['name'], context):
            validated_matches.append(player)
            log_info(f"MATCH VALIDATED: {player['name']} ({player['team']}) in {context} context")
        else:
            log_info(f"MATCH REJECTED: {player['name']} ({player['team']}) - failed {context} validation")
    
    log_info(f"VALIDATION SUMMARY: {len(matches)} → {len(validated_matches)} matches (context: {context})")
    return validated_matches
