#!/usr/bin/env python3
"""
Test script to verify the Seth Lugo comma detection fix.
"""

import sys
import os

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import load_players_from_json
from player_matching import check_player_mentioned

def test_seth_lugo_fix():
    """Test the Seth Lugo comma detection fix"""
    
    print("Loading players data...")
    loaded_players = load_players_from_json("players.json")
    print(f"Loaded {len(loaded_players)} players")
    
    test_query = "seth lugo went +2 to 78 last update, what's the path to gold looking like?"
    print(f"\nTesting query: '{test_query}'")
    print("=" * 80)
    
    result = check_player_mentioned(test_query)
    
    print(f"\nResult: {result}")
    
    if result == "BLOCKED":
        print("❌ FAILURE: Query was incorrectly BLOCKED - this should be allowed")
        print("   This is a single-player question about Seth Lugo with natural language comma")
    elif isinstance(result, list) and len(result) >= 1:
        print(f"✅ SUCCESS: Found {len(result)} players (should be Seth Lugo disambiguation):")
        for player in result:
            print(f"  - {player['name']} ({player['team']})")
        
        # Check if Seth Lugo is in the results
        seth_lugo_found = any('seth lugo' in player['name'].lower() for player in result)
        if seth_lugo_found:
            print("✅ PERFECT: Seth Lugo found in results as expected")
        else:
            print("⚠️  PARTIAL: Results found but Seth Lugo not among them")
    elif result:
        print(f"✅ SUCCESS: Found single player: {result['name']} ({result['team']})")
        if 'seth lugo' in result['name'].lower():
            print("✅ PERFECT: Seth Lugo found as expected")
        else:
            print("⚠️  PARTIAL: Different player found")
    else:
        print("❌ FAILURE: No players found - Seth Lugo should have been detected")

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
        result = check_player_mentioned(test_case)
        if result == "BLOCKED":
            print("❌ INCORRECTLY BLOCKED")
        elif result:
            if isinstance(result, list):
                print(f"✅ ALLOWED: Found {len(result)} players")
            else:
                print(f"✅ ALLOWED: Found {result['name']}")
        else:
            print("⚠️  NO MATCH: No players found")

if __name__ == "__main__":
    test_seth_lugo_fix()
