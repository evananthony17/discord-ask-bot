#!/usr/bin/env python3
"""
Simple test to verify intent detection functions work correctly.
"""

import sys
import os

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import load_players_from_json
from player_matching import has_multi_player_keywords_enhanced, validate_suspicious_names_strict

def test_intent_detection():
    """Test intent detection with the problematic query"""
    
    print("Loading players data...")
    loaded_players = load_players_from_json("players.json")
    print(f"Loaded {len(loaded_players)} players")
    
    test_query = "who should I invest in caminero or Corey Seager"
    print(f"\nTesting query: '{test_query}'")
    
    print("\n=== STEP 1: Intent Detection ===")
    try:
        has_intent, segments = has_multi_player_keywords_enhanced(test_query)
        print(f"Intent detected: {has_intent}")
        print(f"Segments: {segments}")
        
        if has_intent:
            print("\n=== STEP 2: Validation ===")
            confirmed_players = validate_suspicious_names_strict(test_query, segments)
            print(f"Confirmed players: {len(confirmed_players)}")
            
            if confirmed_players:
                for player in confirmed_players:
                    print(f"  - {player['name']} ({player['team']})")
                
                # Check last names
                from utils import normalize_name
                last_names = set()
                for player in confirmed_players:
                    last_name = normalize_name(player['name']).split()[-1]
                    last_names.add(last_name)
                
                print(f"Unique last names: {len(last_names)} - {list(last_names)}")
                
                if len(confirmed_players) >= 2 and len(last_names) >= 2:
                    print("🚫 RESULT: Would be BLOCKED (multi-player)")
                else:
                    print("✅ RESULT: Would be ALLOWED (not enough players or same last name)")
            else:
                print("✅ RESULT: Would be ALLOWED (no confirmed players)")
        else:
            print("✅ RESULT: Would be ALLOWED (no intent detected)")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_intent_detection()
