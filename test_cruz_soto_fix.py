#!/usr/bin/env python3
"""
Test script to verify the Cruz or Soto validation fix.
"""

import sys
import os

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import load_players_from_json
from player_matching import check_player_mentioned

def test_cruz_soto_fix():
    """Test the Cruz or Soto validation fix"""
    
    print("Loading players data...")
    loaded_players = load_players_from_json("players.json")
    print(f"Loaded {len(loaded_players)} players")
    
    test_query = "Should I invest in Cruz or Soto"
    print(f"\nTesting query: '{test_query}'")
    print("=" * 60)
    
    result = check_player_mentioned(test_query)
    
    print(f"\nResult: {result}")
    
    if result == "BLOCKED":
        print("✅ SUCCESS: Query was correctly BLOCKED as multi-player")
    elif isinstance(result, list) and len(result) > 1:
        print(f"⚠️  PARTIAL SUCCESS: Found {len(result)} players:")
        for player in result:
            print(f"  - {player['name']} ({player['team']})")
        
        # Check if we have different last names
        from utils import normalize_name
        last_names = set()
        for player in result:
            last_name = normalize_name(player['name']).split()[-1]
            last_names.add(last_name)
        
        print(f"  Last names: {list(last_names)}")
        
        if len(last_names) > 1:
            print("✅ SUCCESS: Multiple different last names detected - should be blocked")
        else:
            print("❌ ISSUE: Same last names - would show disambiguation instead of blocking")
    else:
        print("❌ FAILURE: Query was not blocked and didn't find multiple players")
        if result:
            if isinstance(result, list):
                print(f"  Found {len(result)} players: {[p['name'] for p in result]}")
            else:
                print(f"  Found single player: {result['name']}")

if __name__ == "__main__":
    test_cruz_soto_fix()
