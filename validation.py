import re
from config import banned_categories

# -------- BANNED WORD CHECKING --------

def contains_banned_word(text):
    """Check if text contains banned words using word boundaries"""
    text_lower = text.lower()
    for category, data in banned_categories.items():
        for word in data["words"]:
            word_lower = word.lower()
            # Use word boundaries to match whole words only
            if re.search(rf"\b{re.escape(word_lower)}\b", text_lower):
                print(f"🚫 Found banned word '{word}' in category '{category}'")
                return category
    return None

# -------- MENTION DETECTION --------

def contains_mention(text):
    """Check if text contains any @mentions (users, roles, @everyone, @here)"""
    patterns = [
        r'<@!?\d+>',           # User mentions <@123456789> or <@!123456789>
        r'<@&\d+>',            # Role mentions <@&123456789>
        r'@(everyone|here)',   # @everyone and @here
        r'@\w+'                # Plain @username mentions
    ]
    
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

# -------- URL DETECTION --------

def contains_url(text):
    """Check if text contains any URLs"""
    patterns = [
        r'https?://',                                                              # https:// or http://
        r'\b\w+\.(com|org|net|edu|gov|io|co|me|app|ly|gg|tv|fm|tk|ml|ga|cf)\b',  # Common TLDs
        r'discord\.(gg|com)',                                                      # Discord links
        r'\bwww\.\w+'                                                              # www prefix
    ]
    
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

# -------- SERVER EMOTE DETECTION --------

def contains_server_emote(text):
    """Check if text contains custom Discord server emotes"""
    return bool(re.search(r'<a?:\w+:\d+>', text))

# -------- VALIDATION PIPELINE --------

def validate_question(question):
    """
    Validate a question through all checks
    Returns: (is_valid, error_message, error_category)
    """
    
    # Length check
    if len(question) > 300:
        return False, f"Your question is too long ({len(question)} characters). Please keep questions under 300 characters.", "length"
    
    # Server emote check
    if contains_server_emote(question):
        return False, "Server emotes are not allowed in questions. Please ask a text-based question.", "emote"
    
    # Mention check
    if contains_mention(question):
        return False, "@mentions are not allowed in questions. Please ask your question without mentioning anyone.", "mention"
    
    # URL check
    if contains_url(question):
        return False, "URLs are not allowed in questions. Please ask your question without including any links.", "url"
    
    # Banned word check
    banned_category = contains_banned_word(question)
    if banned_category:
        response = banned_categories[banned_category]["response"]
        return False, response, "banned_word"
    
    # All checks passed
    return True, None, None