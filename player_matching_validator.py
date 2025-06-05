import re
from difflib import SequenceMatcher
from config import players_data
from utils import normalize_name
from logging_system import log_info

def is_valid_player_name_phrase(phrase, matched_player_name):
    """
    Validate if a phrase actually looks like it could be referring to a player name
    This catches false positives like "more like" matching to "Mike" + "Like"
    """
    phrase_normalized = normalize_name(phrase).lower()
    player_normalized = normalize_name(matched_player_name).lower()
    
    # Split into words
    phrase_words = phrase_normalized.split()
    player_words = player_normalized.split()
    
    log_info(f"VALIDATING: '{phrase}' → '{matched_player_name}'")
    log_info(f"PHRASE WORDS: {phrase_words}")
    log_info(f"PLAYER WORDS: {player_words}")
    
    # Rule 1: Reject obvious non-name phrase patterns
    non_name_patterns = [
        # Common phrase patterns that aren't names
        r'\bmore like\b', r'\bless like\b', r'\bmuch like\b', r'\bjust like\b',
        r'\blooks like\b', r'\bseems like\b', r'\bfeels like\b', r'\bsounds like\b',
        r'\bhow about\b', r'\bwhat about\b', r'\bhow are\b', r'\bwhat are\b',
        r'\bhow is\b', r'\bwhat is\b', r'\bhow was\b', r'\bwhat was\b',
        r'\bgoing to\b', r'\bwant to\b', r'\bneed to\b', r'\btrying to\b',
        r'\bused to\b', r'\bable to\b', r'\bgoing for\b', r'\blooking for\b',
        r'\bthinking about\b', r'\btalking about\b', r'\basking about\b',
        r'\bworried about\b', r'\bexcited about\b', r'\bhappy about\b',
        r'\bsad about\b', r'\bmad about\b', r'\bangry about\b',
        r'\bproud of\b', r'\btired of\b', r'\bsick of\b', r'\bfull of\b',
        r'\bkind of\b', r'\bsort of\b', r'\btype of\b', r'\bout of\b',
        r'\binstead of\b', r'\bbecause of\b', r'\bin case\b', r'\bin fact\b',
        r'\bof course\b', r'\bfor sure\b', r'\bfor real\b', r'\bfor now\b',
        r'\bright now\b', r'\bjust now\b', r'\bby now\b', r'\buntil now\b',
        r'\bso far\b', r'\bso good\b', r'\bso bad\b', r'\bso much\b',
        r'\btoo much\b', r'\btoo many\b', r'\btoo bad\b', r'\btoo good\b',
        r'\bvery much\b', r'\bvery good\b', r'\bvery bad\b', r'\bvery nice\b',
        r'\bpretty good\b', r'\bpretty bad\b', r'\bpretty nice\b', r'\bpretty cool\b',
        r'\bquite good\b', r'\bquite bad\b', r'\bquite nice\b', r'\bquite cool\b',
        r'\breally good\b', r'\breally bad\b', r'\breally nice\b', r'\breally cool\b',
        # Question patterns
        r'\bhow do\b', r'\bwhat do\b', r'\bwhen do\b', r'\bwhere do\b', r'\bwhy do\b',
        r'\bhow can\b', r'\bwhat can\b', r'\bwhen can\b', r'\bwhere can\b', r'\bwhy can\b',
        r'\bhow will\b', r'\bwhat will\b', r'\bwhen will\b', r'\bwhere will\b', r'\bwhy will\b',
        r'\bhow should\b', r'\bwhat should\b', r'\bwhen should\b', r'\bwhere should\b', r'\bwhy should\b',
        # Time/date patterns
        r'\blast week\b', r'\bnext week\b', r'\bthis week\b', r'\bevery week\b',
        r'\blast month\b', r'\bnext month\b', r'\bthis month\b', r'\bevery month\b',
        r'\blast year\b', r'\bnext year\b', r'\bthis year\b', r'\bevery year\b',
        r'\blast night\b', r'\blast day\b', r'\bnext day\b', r'\bthis day\b',
        r'\byesterday was\b', r'\btomorrow is\b', r'\btoday is\b', r'\btonight is\b',
        # Stats/projection patterns
        r'\bmax projection\b', r'\bmin projection\b', r'\bhigh projection\b', r'\blow projection\b',
        r'\bbest case\b', r'\bworst case\b', r'\baverage case\b', r'\bbase case\b',
        r'\bupside potential\b', r'\bdownside risk\b', r'\bceiling projection\b', r'\bfloor projection\b',
        # Fantasy patterns
        r'\bstart or\b', r'\bsit or\b', r'\bbuy or\b', r'\bsell or\b', r'\btrade or\b',
        r'\bpick up\b', r'\bdrop for\b', r'\bwaiver wire\b', r'\bfree agent\b',
        # Comparison patterns
        r'\bbetter than\b', r'\bworse than\b', r'\bsame as\b', r'\bsimilar to\b',
        r'\bcompared to\b', r'\bversus\b', r'\bagainst\b', r'\bover\b'
    ]
    
    for pattern in non_name_patterns:
        if re.search(pattern, phrase_normalized):
            log_info(f"VALIDATION FAILED: Phrase '{phrase}' matches non-name pattern: {pattern}")
            return False
    
    # Rule 2: Check if phrase has reasonable name structure
    if len(phrase_words) == 2:
        word1, word2 = phrase_words
        
        # Both words should be reasonable name length
        if len(word1) < 2 or len(word2) < 2:
            log_info(f"VALIDATION FAILED: Words too short: {word1}, {word2}")
            return False
        
        # Check for obvious non-name word combinations
        non_name_combos = {
            ('more', 'like'), ('less', 'like'), ('much', 'like'), ('just', 'like'),
            ('how', 'about'), ('what', 'about'), ('how', 'are'), ('what', 'are'),
            ('how', 'is'), ('what', 'is'), ('how', 'was'), ('what', 'was'),
            ('going', 'to'), ('want', 'to'), ('need', 'to'), ('trying', 'to'),
            ('used', 'to'), ('able', 'to'), ('have', 'to'), ('got', 'to'),
            ('right', 'now'), ('just', 'now'), ('for', 'now'), ('until', 'now'),
            ('so', 'far'), ('so', 'good'), ('so', 'bad'), ('so', 'much'),
            ('too', 'much'), ('too', 'many'), ('too', 'bad'), ('too', 'good'),
            ('very', 'much'), ('very', 'good'), ('very', 'bad'), ('very', 'nice'),
            ('pretty', 'good'), ('pretty', 'bad'), ('pretty', 'nice'), ('pretty', 'cool'),
            ('really', 'good'), ('really', 'bad'), ('really', 'nice'), ('really', 'cool'),
            ('kind', 'of'), ('sort', 'of'), ('type', 'of'), ('out', 'of'),
            ('instead', 'of'), ('because', 'of'), ('proud', 'of'), ('tired', 'of'),
            ('last', 'week'), ('next', 'week'), ('this', 'week'), ('every', 'week'),
            ('last', 'month'), ('next', 'month'), ('this', 'month'), ('every', 'month'),
            ('last', 'year'), ('next', 'year'), ('this', 'year'), ('every', 'year'),
            ('last', 'night'), ('last', 'day'), ('next', 'day'), ('this', 'day'),
            ('max', 'projection'), ('min', 'projection'), ('high', 'projection'), ('low', 'projection'),
            ('best', 'case'), ('worst', 'case'), ('average', 'case'), ('base', 'case'),
            ('start', 'or'), ('sit', 'or'), ('buy', 'or'), ('sell', 'or'),
            ('pick', 'up'), ('drop', 'for'), ('better', 'than'), ('worse', 'than'),
            ('same', 'as'), ('similar', 'to'), ('compared', 'to')
        }
        
        if (word1, word2) in non_name_combos:
            log_info(f"VALIDATION FAILED: Non-name combo detected: {word1}, {word2}")
            return False
    
    # Rule 3: Check similarity between phrase and player name
    # If the similarity is very low, it's probably a false positive
    similarity = SequenceMatcher(None, phrase_normalized, player_normalized).ratio()
    
    # For multi-word phrases, require higher similarity
    if len(phrase_words) >= 2 and similarity < 0.6:
        log_info(f"VALIDATION FAILED: Low similarity {similarity:.3f} for multi-word phrase")
        return False
    
    # Rule 4: Check if phrase words actually appear in player name
    if len(phrase_words) >= 2:
        # At least one word from the phrase should appear in the player name
        phrase_words_in_player = sum(1 for word in phrase_words if word in player_words)
        if phrase_words_in_player == 0:
            log_info(f"VALIDATION FAILED: No phrase words found in player name")
            return False
    
    # Rule 5: Check for common non-name words in the phrase
    common_non_name_words = {
        'the', 'and', 'or', 'but', 'if', 'then', 'when', 'where', 'why', 'how',
        'what', 'who', 'which', 'that', 'this', 'these', 'those', 'a', 'an',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'could', 'should', 'can', 'may',
        'might', 'must', 'shall', 'to', 'of', 'in', 'on', 'at', 'by', 'for',
        'with', 'without', 'about', 'above', 'below', 'over', 'under', 'up',
        'down', 'out', 'off', 'away', 'back', 'here', 'there', 'now', 'then',
        'today', 'tomorrow', 'yesterday', 'always', 'never', 'sometimes',
        'often', 'usually', 'rarely', 'more', 'less', 'most', 'least', 'much',
        'many', 'few', 'some', 'any', 'all', 'every', 'each', 'both', 'either',
        'neither', 'good', 'bad', 'better', 'worse', 'best', 'worst', 'nice',
        'great', 'awesome', 'terrible', 'horrible', 'amazing', 'fantastic',
        'perfect', 'awful', 'wonderful', 'excellent', 'outstanding', 'impressive',
        'like', 'love', 'hate', 'want', 'need', 'hope', 'think', 'know',
        'believe', 'feel', 'see', 'hear', 'say', 'tell', 'ask', 'answer',
        'give', 'take', 'get', 'put', 'make', 'let', 'help', 'try', 'keep',
        'start', 'stop', 'continue', 'finish', 'end', 'begin', 'come', 'go',
        'bring', 'send', 'find', 'look', 'watch', 'listen', 'read', 'write',
        'play', 'work', 'live', 'stay', 'leave', 'move', 'turn', 'open',
        'close', 'cut', 'break', 'fix', 'build', 'create', 'destroy', 'kill',
        'die', 'born', 'grow', 'change', 'become', 'seem', 'appear', 'happen',
        'occur', 'exist', 'matter', 'mean', 'understand', 'remember', 'forget',
        'learn', 'teach', 'study', 'practice', 'train', 'exercise', 'run',
        'walk', 'drive', 'ride', 'fly', 'swim', 'dance', 'sing', 'talk',
        'speak', 'laugh', 'cry', 'smile', 'sleep', 'wake', 'eat', 'drink',
        'buy', 'sell', 'pay', 'cost', 'spend', 'save', 'win', 'lose', 'beat',
        'fight', 'argue', 'agree', 'disagree', 'choose', 'decide', 'pick',
        'select', 'prefer', 'enjoy', 'mind', 'care', 'worry', 'fear', 'trust',
        'doubt', 'guess', 'suppose', 'imagine', 'dream', 'wish', 'plan',
        'prepare', 'organize', 'arrange', 'manage', 'control', 'lead', 'follow',
        'join', 'meet', 'visit', 'call', 'contact', 'reach', 'touch', 'hold',
        'carry', 'lift', 'push', 'pull', 'throw', 'catch', 'hit', 'kick',
        'jump', 'climb', 'fall', 'drop', 'rise', 'raise', 'lower', 'increase',
        'decrease', 'add', 'remove', 'include', 'exclude', 'contain', 'cover',
        'protect', 'attack', 'defend', 'support', 'oppose', 'resist', 'accept',
        'reject', 'approve', 'disapprove', 'allow', 'forbid', 'permit', 'ban',
        'force', 'pressure', 'influence', 'affect', 'impact', 'cause', 'result',
        'lead', 'follow', 'guide', 'direct', 'point', 'show', 'hide', 'reveal',
        'discover', 'explore', 'search', 'investigate', 'examine', 'check',
        'test', 'try', 'attempt', 'succeed', 'fail', 'pass', 'miss', 'catch',
        'lose', 'find', 'keep', 'save', 'waste', 'use', 'apply', 'employ',
        'hire', 'fire', 'quit', 'retire', 'rest', 'relax', 'enjoy', 'suffer',
        'hurt', 'heal', 'cure', 'treat', 'help', 'harm', 'damage', 'repair'
    }
    
    # If phrase consists mostly of common non-name words, reject it
    non_name_word_count = sum(1 for word in phrase_words if word in common_non_name_words)
    if len(phrase_words) >= 2 and non_name_word_count >= len(phrase_words) - 1:
        log_info(f"VALIDATION FAILED: Phrase consists mostly of non-name words")
        return False
    
    log_info(f"VALIDATION PASSED: '{phrase}' → '{matched_player_name}'")
    return True

def validate_player_matches(text, matches):
    """
    Filter out false positive matches using phrase validation
    """
    if not matches:
        return matches
    
    validated_matches = []
    
    for player in matches:
        if is_valid_player_name_phrase(text, player['name']):
            validated_matches.append(player)
            log_info(f"MATCH VALIDATED: {player['name']} ({player['team']})")
        else:
            log_info(f"MATCH REJECTED: {player['name']} ({player['team']}) - failed validation")
    
    log_info(f"VALIDATION SUMMARY: {len(matches)} → {len(validated_matches)} matches")
    return validated_matches
