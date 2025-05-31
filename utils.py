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
    normalized = normalize_name(text)
    words = normalized.split()
    
    # Very short queries are probably not player requests unless they look like names
    if len(words) == 1 and len(words[0]) <= 4:
        return False
    
    # Look for obvious non-player patterns using WORD BOUNDARIES
    casual_patterns = [
        r'\bmore like\b', r'\blol\b', r'\bhaha\b', r'\bthanks\b', r'\bthank you\b',
        r'\bgood job\b', r'\bnice job\b', r'\bwell done\b', r'\bcool\b', r'\bwow\b',
        r'\byeah\b', r'\byes\b', r'\bno\b', r'\bok\b', r'\bokay\b', r'\bwhat the\b',
        r'\bwtf\b', r'\bomg\b'
    ]
    
    for pattern in casual_patterns:
        if re.search(pattern, normalized):
            return False
    
    # If it's a short question with no obvious player name indicators, probably casual
    if '?' in text and len(words) <= 3:
        original_words = text.split()
        name_like = any(
            len(word.strip('.,!?')) >= 5 and word.strip('.,!?')[0].isupper()
            for word in original_words
        )
        if not name_like:
            return False
    
    return True

# -------- TIME FORMATTING --------

def format_time_ago(time_delta):
    """Format a timedelta object into a human-readable string"""
    if time_delta.days > 0:
        return f"{time_delta.days} day{'s' if time_delta.days > 1 else ''}"
    elif time_delta.seconds > 3600:
        hours = time_delta.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''}"
    elif time_delta.seconds > 60:
        minutes = time_delta.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''}"
    else:
        return "just now"

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