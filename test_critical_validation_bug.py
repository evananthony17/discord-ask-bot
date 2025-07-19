#!/usr/bin/env python3

"""
Test script to reproduce the critical validation bug where common English words
are being treated as player names and validated.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot_logic import get_potential_player_words
from player_matching_validator import validate_player_matches

def test_critical_validation_bug():
    """Test the exact scenario from the logs"""
    print("=" * 60)
    print("TESTING CRITICAL VALIDATION BUG")
    print("=" * 60)
    
    # The exact question from the logs
    question = "should we bail on Okert or is it early enough that he can make up for tonight? - posting for Wrath who had question blocked due to bot issue"
    
    print(f"Question: {question}")
    print()
    
    # Step 1: Extract potential player words (this is what bot.py does)
    print("1. Extracting potential player words:")
    potential_player_words = get_potential_player_words(question)
    print(f"   Potential words: {potential_player_words}")
    print()
    
    # Step 2: Create mock players (this is what bot.py does)
    print("2. Creating mock players:")
    mock_players = [{'name': word, 'team': 'Unknown'} for word in potential_player_words]
    print(f"   Mock players: {[p['name'] for p in mock_players]}")
    print()
    
    # Step 3: Validate these mock players (this is where the bug occurs)
    print("3. Validating mock players:")
    validated_words = validate_player_matches(question, mock_players)
    print(f"   Validated words: {[p['name'] for p in validated_words]}")
    print()
    
    # Step 4: Show the problem
    print("4. Analysis:")
    if validated_words:
        print(f"   ❌ BUG CONFIRMED: {len(validated_words)} common words validated as players!")
        for word in validated_words:
            print(f"      - '{word['name']}' was validated as a player name")
    else:
        print(f"   ✅ GOOD: No common words validated as players")
    
    print()

def test_individual_words():
    """Test individual problematic words"""
    print("=" * 60)
    print("TESTING INDIVIDUAL PROBLEMATIC WORDS")
    print("=" * 60)
    
    # Test the specific words that were validated in the logs
    problematic_words = ['should', 'bail', 'early', 'enough', 'that', 'make', 'tonight', 'posting', 'wrath', 'blocked', 'issue']
    
    question = "should we bail on Okert or is it early enough that he can make up for tonight? - posting for Wrath who had question blocked due to bot issue"
    
    for word in problematic_words:
        print(f"Testing word: '{word}'")
        mock_players = [{'name': word, 'team': 'Unknown'}]
        validated = validate_player_matches(question, mock_players)
        
        if validated:
            print(f"   ❌ '{word}' was validated as a player name!")
        else:
            print(f"   ✅ '{word}' was correctly rejected")
        print()

if __name__ == "__main__":
    test_critical_validation_bug()
    test_individual_words()
