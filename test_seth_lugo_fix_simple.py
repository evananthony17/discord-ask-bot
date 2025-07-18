#!/usr/bin/env python3
"""
Test script to verify the Seth Lugo comma detection fix (without asyncio).
"""

import sys
import os

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import load_players_from_json
from player_matching import has_multi_player_keywords_enhanced, simplified_player_detection

def test_seth_lugo_fix():
    """Test the Seth Lugo comma detection fix"""
    
    print("Loading players data...")
    loaded_players = load_players_from_json("players.json")
    print(f"Loaded {len(loaded_players)} players")
    
    test_query = "seth lugo went +2 to 78 last update, what's the path to gold looking like?"
    print(f"\nTesting query: '{test_query}'")
    print("=" * 80)
    
    # Test the comma detection directly
    print("Step 1: Testing comma detection...")
    has_intent, segments = has_multi_player_keywords_enhanced(test_query)
    
    if has_intent:
        print(f"❌ FAILURE: Comma detection incorrectly triggered multi-player intent")
        print(f"   Segments: {segments}")
    else:
        print(f"✅ SUCCESS: Comma detection correctly rejected multi-player intent")
    
    # Test the simplified player detection
    print("\nStep 2: Testing player detection...")
    try:
        result = simplified_player_detection(test_query)
        
        if result:
            if isinstance(result, list):
                print(f"✅ SUCCESS: Found {len(result)} players:")
                for player in result:
                    print(f"  - {player['name']} ({player['team']})")
                
                # Check if Seth Lugo is in the results
                seth_lugo_found = any('seth lugo' in player['name'].lower() for player in result)
                if seth_lugo_found:
                    print("✅ PERFECT: Seth Lugo found in results as expected")
                else:
                    print("⚠️  PARTIAL: Results found but Seth Lugo not among them")
            else:
                print(f"✅ SUCCESS: Found single player: {result['name']} ({result['team']})")
                if 'seth lugo' in result['name'].lower():
                    print("✅ PERFECT: Seth Lugo found as expected")
                else:
                    print("⚠️  PARTIAL: Different player found")
        else:
            print("❌ FAILURE: No players found - Seth Lugo should have been detected")
    except Exception as e:
        print(f"❌ ERROR: Exception during player detection: {e}")

    # Test a few more natural language comma cases
    print("\n" + "=" * 80)
    print("Testing additional natural language comma cases:")
    
    additional_tests = [
        "how is judge doing lately, any updates?",
        "trout has been struggling, what do you think?", 
        "ohtani pitched well yesterday, should I start him?",
        "acuna is heating up, worth picking up?"
    ]
    
    for test_case in additional_tests:
        print(f"\nTesting: '{test_case}'")
        has_intent, _ = has_multi_player_keywords_enhanced(test_case)
        if has_intent:
            print("❌ INCORRECTLY DETECTED AS MULTI-PLAYER")
        else:
            print("✅ CORRECTLY REJECTED MULTI-PLAYER INTENT")

if __name__ == "__main__":
    test_seth_lugo_fix()
