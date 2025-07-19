#!/usr/bin/env python3

"""
Simple test to verify the validation fix works
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from player_matching_validator import validate_player_matches

def test_simple_fix():
    """Test that common English words are now rejected"""
    print("Testing validation fix...")
    
    question = "should we bail on Okert or is it early enough that he can make up for tonight?"
    
    # Test individual common words
    common_words = ['should', 'bail', 'early', 'enough', 'that', 'make', 'tonight', 'posting', 'blocked', 'issue']
    
    for word in common_words:
        mock_players = [{'name': word, 'team': 'Unknown'}]
        validated = validate_player_matches(question, mock_players)
        
        if validated:
            print(f"❌ STILL BROKEN: '{word}' was validated as a player name!")
            return False
        else:
            print(f"✅ FIXED: '{word}' was correctly rejected")
    
    # Test that real player names still work
    real_player = [{'name': 'okert', 'team': 'Giants'}]
    validated = validate_player_matches(question, real_player)
    
    if validated:
        print(f"✅ GOOD: Real player 'okert' was correctly validated")
    else:
        print(f"❌ PROBLEM: Real player 'okert' was incorrectly rejected")
        return False
    
    print("\n🎉 ALL TESTS PASSED - Validation fix is working!")
    return True

if __name__ == "__main__":
    test_simple_fix()
