#!/usr/bin/env python3

"""
Test script to reproduce and verify fixes for:
1. Okert issue: "should we bail on Okert or is it early enough that he can make up for tonight?"
2. Brayan vs Wilyer Abreu issue: lastname matching in recent mentions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from player_matching import check_player_mentioned, has_multi_player_keywords_enhanced
from recent_mentions import check_player_mention_hierarchical
from utils import normalize_name

def test_okert_issue():
    """Test the Okert question that's being incorrectly blocked"""
    print("=" * 60)
    print("TESTING OKERT ISSUE")
    print("=" * 60)
    
    # The exact question from the logs
    question = "should we bail on Okert or is it early enough that he can make up for tonight?"
    
    print(f"Question: {question}")
    print()
    
    # Test multi-player intent detection
    print("1. Testing multi-player intent detection:")
    has_intent, segments = has_multi_player_keywords_enhanced(question)
    print(f"   Has multi-player intent: {has_intent}")
    print(f"   Segments: {segments}")
    print()
    
    # Test unified player detection
    print("2. Testing unified player detection:")
    result = check_player_mentioned(question)
    print(f"   Result: {result}")
    print(f"   Type: {type(result)}")
    
    if result == "BLOCKED":
        print("   ❌ ISSUE CONFIRMED: Question is being blocked")
    elif result and isinstance(result, list):
        print(f"   ✅ GOOD: Found {len(result)} players: {[p['name'] for p in result]}")
    elif result:
        print(f"   ✅ GOOD: Found single player: {result['name']}")
    else:
        print("   ⚠️  No players found")
    
    print()

def test_brayan_abreu_issue():
    """Test the Brayan vs Wilyer Abreu lastname matching issue"""
    print("=" * 60)
    print("TESTING BRAYAN VS WILYER ABREU ISSUE")
    print("=" * 60)
    
    # Simulate a recent mention of "Wilyer Abreu" in expert reply
    expert_reply = "I have Wilyer Abreu as a solid pickup for steals category. He's been performing well lately."
    
    # Test if "Brayan Abreu" question would be blocked by this
    brayan_question = "What are your thoughts on Brayan Abreu?"
    
    print(f"Expert reply (recent): {expert_reply}")
    print(f"New question: {brayan_question}")
    print()
    
    # Test hierarchical matching for both players
    print("1. Testing if 'Brayan Abreu' matches in expert reply about 'Wilyer Abreu':")
    
    brayan_normalized = normalize_name("Brayan Abreu")
    wilyer_normalized = normalize_name("Wilyer Abreu")
    expert_normalized = normalize_name(expert_reply)
    
    print(f"   Brayan normalized: {brayan_normalized}")
    print(f"   Wilyer normalized: {wilyer_normalized}")
    print(f"   Expert reply normalized: {expert_normalized}")
    print()
    
    # Test the hierarchical matching
    is_match, match_type, confidence = check_player_mention_hierarchical(
        brayan_normalized, "brayan_uuid", expert_normalized, expert_reply, "Expert"
    )
    
    print(f"   Match result: {is_match}")
    print(f"   Match type: {match_type}")
    print(f"   Confidence: {confidence}")
    
    if is_match:
        print("   ❌ ISSUE CONFIRMED: Brayan Abreu incorrectly matches Wilyer Abreu mention")
    else:
        print("   ✅ GOOD: Brayan Abreu does not match Wilyer Abreu mention")
    
    print()

def test_fixes():
    """Test that our fixes work correctly"""
    print("=" * 60)
    print("TESTING PROPOSED FIXES")
    print("=" * 60)
    
    # Test cases that should work correctly
    test_cases = [
        # Single player with "or" (should NOT be blocked)
        "should we bail on Okert or is it early enough that he can make up for tonight?",
        "Is Soto playing today or is he sitting?",
        "Should I start Judge or bench him?",
        
        # True multi-player (should be blocked)
        "Who is better, Soto or Judge?",
        "Should I start Soto or Judge?",
        "Soto vs Judge for tonight?",
        
        # Disambiguation cases (should show options)
        "How is Suarez doing?",  # Multiple Suarez players
        "What about Chapman?",   # Multiple Chapman players
    ]
    
    for i, question in enumerate(test_cases, 1):
        print(f"{i}. Testing: {question}")
        
        # Test intent detection
        has_intent, segments = has_multi_player_keywords_enhanced(question)
        print(f"   Intent detected: {has_intent}")
        if has_intent:
            print(f"   Segments: {segments}")
        
        # Test player detection
        result = check_player_mentioned(question)
        if result == "BLOCKED":
            print(f"   Result: BLOCKED")
        elif result and isinstance(result, list):
            print(f"   Result: {len(result)} players found")
        elif result:
            print(f"   Result: Single player found")
        else:
            print(f"   Result: No players found")
        
        print()

if __name__ == "__main__":
    test_okert_issue()
    test_brayan_abreu_issue()
    test_fixes()
