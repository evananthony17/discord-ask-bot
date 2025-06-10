import json
import os
import unicodedata
from datetime import timedelta
import re
from config import player_nicknames, players_data
from logging_system import log_info, log_warning, log_error, log_debug

# -------- NAME NORMALIZATION --------

def normalize_name(name):
    """Normalize player names for better matching - handle accents, case, punctuation"""
    # Remove accents and diacritics (Acuña → Acuna)
    normalized = unicodedata.normalize('NFD', name)
    ascii_name = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    
    # Convert to lowercase
    ascii_name = ascii_name.lower()
    
    # Handle apostrophes consistently - remove them (O'Neil → oneil)
    ascii_name = ascii_name.replace("'", "").replace("'", "")  # Handle both straight and curly apostrophes
    
    # Remove common punctuation and extra spaces
    ascii_name = ascii_name.replace('.', '').replace(',', '').replace('-', ' ')
    ascii_name = ' '.join(ascii_name.split())  # Remove extra whitespace
    
    return ascii_name

# -------- NICKNAME SYSTEM --------

def load_nicknames_from_json(filename):
    """Load player nicknames from JSON file"""
    global player_nicknames
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                loaded_nicknames = json.load(f)
                player_nicknames.clear()
                player_nicknames.update({k.lower(): v.lower() for k, v in loaded_nicknames.items()})
                log_info(f"NICKNAMES: Loaded {len(player_nicknames)} nicknames")
                return True
        else:
            # Create example file with common nicknames
            example_nicknames = {
                "jram": "jose ramirez",
                "judge": "aaron judge",
                "trout": "mike trout",
                "vlad jr": "vladimir guerrero jr",
                "vladdy": "vladimir guerrero jr",
                "tatis": "fernando tatis jr",
                "tatis jr": "fernando tatis jr",
                "big papi": "david ortiz",
                "papi": "david ortiz",
                "miggy": "miguel cabrera",
                "ohtani": "shohei ohtani",
                "sho time": "shohei ohtani",
                "showtime": "shohei ohtani",
                "mookie": "mookie betts",
                "freddie": "freddie freeman",
                "bryce": "bryce harper",
                "harper": "bryce harper",
                "machado": "manny machado",
                "altuve": "jose altuve",
                "lindor": "francisco lindor",
                "degrom": "jacob degrom",
                "scherzer": "max scherzer",
                "mad max": "max scherzer",
                "verlander": "justin verlander",
                "jv": "justin verlander",
                "kershaw": "clayton kershaw",
                "cole": "gerrit cole"
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(example_nicknames, f, indent=2, ensure_ascii=False)
            
            player_nicknames.clear()
            player_nicknames.update({k.lower(): v.lower() for k, v in example_nicknames.items()})
            log_info(f"NICKNAMES: Created example file with {len(player_nicknames)} nicknames")
            return True
    except Exception as e:
        log_error(f"NICKNAMES: Error loading {filename}: {e}")
        player_nicknames.clear()
        return False

def expand_nicknames(text):
    """Convert nicknames to full player names"""
    if not player_nicknames:
        return text
    
    text_lower = text.lower().strip()
    log_debug(f"NICKNAME: Processing '{text_lower}'")
    
    # Check for exact nickname matches
    if text_lower in player_nicknames:
        expanded = player_nicknames[text_lower]
        log_info(f"NICKNAME EXPANSION: '{text}' → '{expanded}'")
        return expanded
    
    # Check word-by-word
    words = text_lower.split()
    expanded_words = []
    nickname_found = False
    
    for word in words:
        if word in player_nicknames:
            expanded_words.append(player_nicknames[word])
            nickname_found = True
            log_info(f"NICKNAME EXPANSION: '{word}' → '{player_nicknames[word]}'")
        else:
            expanded_words.append(word)
    
    if nickname_found:
        result = ' '.join(expanded_words)
        log_info(f"NICKNAME RESULT: '{text}' → '{result}'")
        return result
    
    return text

# -------- PLAYER REQUEST DETECTION --------

def is_likely_player_request(text):
    """Determine if text is likely asking about a player vs casual conversation"""
    from config import players_data  # Import here to avoid circular imports
    
    normalized = normalize_name(text)
    words = normalized.split()
    
    # 🔧 FIXED: Block obvious non-baseball words immediately
    blocked_words = {
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
        'weather', 'time', 'date', 'clock', 'help', 'what', 'when', 'where',
        'why', 'how', 'love', 'hate', 'like', 'dislike', 'want', 'need'
    }
    
    # If the query consists entirely of blocked words, reject it immediately
    query_words = set(words)
    if query_words.issubset(blocked_words):
        log_info(f"PLAYER REQUEST: Blocked query '{text}' - contains only blocked words")
        return False
    
    # Very short queries are probably not player requests unless they look like names
    if len(words) == 1 and len(words[0]) <= 4:
        single_word = words[0].lower()
        
        # Block the word if it's in our blocked list
        if single_word in blocked_words:
            log_info(f"PLAYER REQUEST: Blocked single word '{single_word}' - in blocked list")
            return False
        
        # For 4-letter words, check if it's likely a surname using WORD BOUNDARIES
        if len(words[0]) == 4:
            word_lower = words[0].lower()
            
            # 🔧 FIXED: Use word boundaries instead of substring matching
            for player in players_data:
                player_name_normalized = normalize_name(player['name']).lower()
                # Check if the word appears as a complete word in the player name
                if re.search(f"\\b{re.escape(word_lower)}\\b", player_name_normalized):
                    log_info(f"PLAYER REQUEST: Approved 4-letter word '{word_lower}' - found as complete word in player database")
                    return True
            
            log_info(f"PLAYER REQUEST: Rejected 4-letter word '{word_lower}' - not found as complete word in player database")
            return False  # 4-letter word but not a known player name component
        else:
            log_info(f"PLAYER REQUEST: Rejected short word '{single_word}' - too short for player name")
            return False  # 1-3 letter words are definitely not player names
    
    # Look for obvious non-player patterns using WORD BOUNDARIES
    casual_patterns = [
        r'\bmore like\b', r'\blol\b', r'\bhaha\b', r'\bthanks\b', r'\bthank you\b',
        r'\bgood job\b', r'\bnice job\b', r'\bwell done\b', r'\bcool\b', r'\bwow\b',
        r'\byeah\b', r'\byes\b', r'\bno\b', r'\bok\b', r'\bokay\b', r'\bwhat the\b',
        r'\bwtf\b', r'\bomg\b', r'\bhow are you\b', r'\bwhats up\b', r'\bwhat\'s up\b',
        r'\bhello there\b', r'\bbye bye\b', r'\bsee you\b', r'\btalk to you\b'
    ]
    
    for pattern in casual_patterns:
        if re.search(pattern, normalized):
            log_info(f"PLAYER REQUEST: Blocked query '{text}' - matched casual pattern: {pattern}")
            return False
    
    # 🔧 FIXED: Check for potential player names in the database with validation
    potential_player_words = []
    for word in words:
        if word not in blocked_words and len(word) >= 4:
            # Check if this word could be part of a player name
            for player in players_data:
                player_name_normalized = normalize_name(player['name']).lower()
                if word.lower() in player_name_normalized.split():
                    potential_player_words.append(word)
                    break
    
    # If we found potential player words, validate them before approving
    if potential_player_words:
        # 🔧 FIX: Validate potential words before approving the request
        try:
            from player_matching_validator import validate_player_matches
            mock_players = [{'name': word, 'team': 'Unknown'} for word in potential_player_words]
            validated_words = validate_player_matches(text, mock_players)
            
            if validated_words:
                log_info(f"PLAYER REQUEST: Approved query '{text}' - found validated player words: {[p['name'] for p in validated_words]}")
                return True
            else:
                log_info(f"PLAYER REQUEST: Rejected query '{text}' - potential words failed validation: {potential_player_words}")
                # Continue to other checks instead of returning False immediately
        except Exception as e:
            log_error(f"PLAYER REQUEST: Error during validation: {e}")
            # Fallback to original behavior if validation fails
            log_info(f"PLAYER REQUEST: Approved query '{text}' - found potential player words (validation failed): {potential_player_words}")
            return True
    
    # 🔧 FALLBACK: Check for question words without proper names (original logic but more lenient)
    question_words = {'what', 'when', 'where', 'why', 'how', 'who', 'which'}
    if any(word in question_words for word in words):
        # If it's a question, require it to have at least one word that could be a name (4+ letters)
        original_words = text.split()
        has_name_like_word = any(
            len(word.strip('.,!?')) >= 4 and word.strip('.,!?').isalpha()
            for word in original_words
        )
        if not has_name_like_word:
            log_info(f"PLAYER REQUEST: Blocked question '{text}' - no name-like words found")
            return False
    
    # If it's a short question with no obvious player name indicators, probably casual
    if '?' in text and len(words) <= 3:
        original_words = text.split()
        name_like = any(
            len(word.strip('.,!?')) >= 4 and word.strip('.,!?').isalpha()
            for word in original_words
        )
        if not name_like:
            log_info(f"PLAYER REQUEST: Blocked short question '{text}' - no name-like words")
            return False
    
    # 🔧 ENHANCED: Additional validation for multi-word queries
    if len(words) >= 2:
        # Check if it contains baseball context OR has potential player names
        baseball_indicators = {
            'player', 'pitcher', 'batter', 'team', 'mlb', 'baseball', 'stats', 
            'era', 'rbi', 'batting', 'home', 'run', 'runs', 'hitting', 'pitching',
            'fantasy', 'roster', 'lineup', 'trade', 'waiver', 'draft', 'update',
            'projection', 'overall', 'season', 'game', 'hurt', 'injured', 'injury'
        }
        
        has_baseball_context = any(word in baseball_indicators for word in words)
        
        # If we already found potential player words above, we're good
        if potential_player_words:
            log_info(f"PLAYER REQUEST: Approved multi-word query '{text}' - contains potential player names")
            return True
        
        # If no player words but has baseball context, still allow
        if has_baseball_context:
            log_info(f"PLAYER REQUEST: Approved multi-word query '{text}' - contains baseball context")
            return True
        
        # Check for name-like word structure (4+ letter words that could be names)
        original_words = text.split()
        name_like_words = [
            word.strip('.,!?') for word in original_words 
            if len(word.strip('.,!?')) >= 4 and word.strip('.,!?').isalpha()
            and word.strip('.,!?').lower() not in blocked_words
        ]
        
        if len(name_like_words) >= 1:
            log_info(f"PLAYER REQUEST: Approved multi-word query '{text}' - contains name-like words: {name_like_words}")
            return True
        
        log_info(f"PLAYER REQUEST: Blocked multi-word query '{text}' - no baseball context, player names, or name-like words")
        return False
    
    log_info(f"PLAYER REQUEST: Approved query '{text}' - passed all filters")
    return True

# -------- FILE LOADING --------

def load_words_from_json(filename):
    """Load words from JSON file"""
    try:
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)
            return [word.strip().lower() for word in data]
    except Exception as e:
        log_error(f"Error loading {filename}: {e}")
        return []

def load_players_from_json(filename):
    """Load players from JSON file"""
    global players_data
    try:
        if not os.path.exists(filename):
            log_error(f"File {filename} does not exist!")
            return []
        
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, list):
                players_data.clear()
                players_data.extend(data)
                return data
            else:
                log_error(f"Expected list in {filename}, got {type(data)}")
                return []
    except Exception as e:
        log_error(f"Error loading {filename}: {e}")
        return []

# -------- LEGACY FUNCTIONS --------

def contains_banned_words(question):
    """Legacy function - Check if question contains any banned words"""
    banned_words = ['spam', 'test123', 'ignore']
    question_lower = question.lower()
    
    for word in banned_words:
        if word in question_lower:
            return True
    return False
