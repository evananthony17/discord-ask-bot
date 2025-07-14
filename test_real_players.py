#!/usr/bin/env python3
"""
Test with real players to verify blocking works.
"""

import sys
import os

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import load_players_from_json, normalize_name
from player_matching import has_multi_player_keywords_enhanced, validate_suspicious_names_strict

def test_real_players():
    """Test intent detection with real players"""
    
    print("Loading players data...")
    loaded_players = load_players_from_json("players.json")
    print(f"Loaded {len(loaded_players)} players")
    
    # Test with real players
    test_queries = [
        "Harper or Trout who is better",
        "Judge and Ohtani comparison", 
        "Soto vs Acuna for ROS",
        "who should I invest in caminero or Corey Seager"  # Original query
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Testing: '{query}'")
        print('='*60)
        
        try:
            # Step 1: Intent detection
            has_intent, segments = has_multi_player_keywords_enhanced(query)
            print(f"Intent detected: {has_intent}")
            print(f"Segments: {segments}")
            
            if has_intent:
                # Step 2: Validation
                confirmed_players = validate_suspicious_names_strict(query, segments)
                print(f"Confirmed players: {len(confirmed_players)}")
                
                if confirmed_players:
                    for player in confirmed_players:
                        print(f"  - {player['name']} ({player['team']})")
                    
                    # Check last names
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
    test_real_players()
