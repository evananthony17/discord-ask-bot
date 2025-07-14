#!/usr/bin/env python3
"""
Test script to verify the multi-player intent detection fix.
Tests the specific "caminero or Corey Seager" case that was failing.
"""

import sys
import os

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from player_matching import has_multi_player_keywords_enhanced, validate_suspicious_names_strict
from utils import normalize_name, load_players_from_json
from config import players_data

# Load players data for testing
print("Loading players data...")
loaded_players = load_players_from_json("players.json")
print(f"Loaded {len(loaded_players)} players")

def test_multi_player_intent_detection():
    """Test the new intent-first multi-player detection system"""
    
    print("🧪 Testing Multi-Player Intent Detection Fix")
    print("=" * 50)
    
    # Test cases that should be blocked
    test_cases_should_block = [
        "who should I invest in caminero or Corey Seager",
        "should i invest in cruz or soto", 
        "Harper vs Trout",
        "Judge and Ohtani",
        "between Soto and Harper who is better",
        "Acuna or Betts for ROS"
    ]
    
    # Test cases that should NOT be blocked
    test_cases_should_allow = [
        "Corey Seager stats",
        "how is Corey or should I bench him",
        "Suarez update",  # Should allow disambiguation
        "Francisco Lindor projection"
    ]
    
    print("\n🚫 Testing cases that SHOULD be blocked:")
    print("-" * 40)
    
    for query in test_cases_should_block:
        print(f"\nQuery: '{query}'")
        
        # Step 1: Intent detection
        has_intent, segments = has_multi_player_keywords_enhanced(query)
        print(f"  Intent detected: {has_intent}")
        print(f"  Segments: {segments}")
        
        if has_intent:
            # Step 2: Validation
            confirmed_players = validate_suspicious_names_strict(query, segments)
            print(f"  Confirmed players: {len(confirmed_players)}")
            
            if confirmed_players:
                player_names = [p['name'] for p in confirmed_players]
                print(f"  Players found: {player_names}")
                
                # Check for different last names
                last_names = set()
                for player in confirmed_players:
                    last_name = normalize_name(player['name']).split()[-1]
                    last_names.add(last_name)
                
                print(f"  Unique last names: {len(last_names)} - {list(last_names)}")
                
                if len(confirmed_players) >= 2 and len(last_names) >= 2:
                    print(f"  ✅ RESULT: Would be BLOCKED (multi-player)")
                else:
                    print(f"  ❌ RESULT: Would be ALLOWED (not enough players or same last name)")
            else:
                print(f"  ❌ RESULT: Would be ALLOWED (no confirmed players)")
        else:
            print(f"  ❌ RESULT: Would be ALLOWED (no intent detected)")
    
    print("\n\n✅ Testing cases that should be ALLOWED:")
    print("-" * 40)
    
    for query in test_cases_should_allow:
        print(f"\nQuery: '{query}'")
        
        # Step 1: Intent detection
        has_intent, segments = has_multi_player_keywords_enhanced(query)
        print(f"  Intent detected: {has_intent}")
        
        if has_intent:
            print(f"  Segments: {segments}")
            # Step 2: Validation
            confirmed_players = validate_suspicious_names_strict(query, segments)
            print(f"  Confirmed players: {len(confirmed_players)}")
            
            if len(confirmed_players) >= 2:
                # Check for different last names
                last_names = set()
                for player in confirmed_players:
                    last_name = normalize_name(player['name']).split()[-1]
                    last_names.add(last_name)
                
                print(f"  Unique last names: {len(last_names)}")
                
                if len(last_names) >= 2:
                    print(f"  ❌ RESULT: Would be BLOCKED (unexpected!)")
                else:
                    print(f"  ✅ RESULT: Would be ALLOWED (same last name - disambiguation)")
            else:
                print(f"  ✅ RESULT: Would be ALLOWED (insufficient confirmed players)")
        else:
            print(f"  ✅ RESULT: Would be ALLOWED (no intent detected)")

def test_corey_splitting_fix():
    """Test that 'Corey' is no longer split into 'C' and 'ey'"""
    
    print("\n\n🔧 Testing 'Corey' Splitting Fix")
    print("=" * 50)
    
    from player_matching import extract_potential_names
    
    test_query = "who should I invest in caminero or Corey Seager"
    print(f"Query: '{test_query}'")
    
    potential_names = extract_potential_names(test_query)
    print(f"Extracted names: {potential_names}")
    
    # Check if we have any single-character names (which would indicate splitting bug)
    single_char_names = [name for name in potential_names if len(name) == 1]
    
    if single_char_names:
        print(f"❌ SPLITTING BUG DETECTED: Found single-character names: {single_char_names}")
    else:
        print(f"✅ SPLITTING FIX WORKING: No single-character names found")
    
    # Check if 'Corey Seager' appears as a complete name
    full_names = [name for name in potential_names if 'corey' in name.lower() and 'seager' in name.lower()]
    if full_names:
        print(f"✅ FULL NAME PRESERVED: Found complete name: {full_names}")
    else:
        print(f"⚠️  FULL NAME NOT FOUND: 'Corey Seager' not found as complete name")

if __name__ == "__main__":
    try:
        test_corey_splitting_fix()
        test_multi_player_intent_detection()
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
