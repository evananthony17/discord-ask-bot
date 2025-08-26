#!/usr/bin/env python3
"""
Debug script to diagnose the production player loading issue
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

def test_production_debug():
    """Debug the production player loading issue"""
    print("🔍 Debugging production player loading issue...")
    
    # Test 1: Check if players.json exists and is readable
    print("\n1️⃣ Checking players.json file...")
    if os.path.exists("players.json"):
        try:
            with open("players.json", "r", encoding="utf-8") as f:
                import json
                data = json.load(f)
                print(f"✅ players.json exists and contains {len(data)} players")
                print(f"📝 Sample player: {data[0] if data else 'No players'}")
        except Exception as e:
            print(f"❌ Error reading players.json: {e}")
    else:
        print("❌ players.json file does not exist!")
    
    # Test 2: Test the load_players_from_json function
    print("\n2️⃣ Testing load_players_from_json function...")
    try:
        from utils import load_players_from_json
        players_loaded = load_players_from_json("players.json")
        print(f"✅ load_players_from_json returned {len(players_loaded)} players")
    except Exception as e:
        print(f"❌ Error in load_players_from_json: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Check the global players_data after loading
    print("\n3️⃣ Checking global players_data...")
    try:
        from config import players_data
        print(f"📊 config.players_data length: {len(players_data)}")
        
        import utils
        print(f"📊 utils.players_data length: {len(utils.players_data)}")
        
        import player_matching
        print(f"📊 player_matching.players_data length: {len(player_matching.players_data)}")
        
        # Check if they're the same object
        print(f"🔗 Same object check:")
        print(f"   config.players_data is utils.players_data: {players_data is utils.players_data}")
        print(f"   config.players_data is player_matching.players_data: {players_data is player_matching.players_data}")
        
    except Exception as e:
        print(f"❌ Error checking global players_data: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Simulate the exact bot startup sequence
    print("\n4️⃣ Simulating bot startup sequence...")
    try:
        # This is what happens in on_ready()
        from utils import load_words_from_json, load_players_from_json
        from config import banned_categories, players_data
        
        print("Loading profanity words...")
        banned_categories["profanity"]["words"] = load_words_from_json("profanity.json")
        print(f"✅ Loaded {len(banned_categories['profanity']['words'])} profanity words")
        
        print("Loading players...")
        players_loaded = load_players_from_json("players.json")
        print(f"✅ Loaded {len(players_loaded)} players")
        
        print("Checking players_data after loading...")
        print(f"📊 players_data length: {len(players_data)}")
        
        if len(players_data) == 0:
            print("❌ CRITICAL: players_data is still empty after loading!")
            print("🔍 Investigating why...")
            
            # Check if the function actually modifies the global
            import utils
            print(f"📊 utils.players_data length: {len(utils.players_data)}")
            
            if len(utils.players_data) > 0:
                print("✅ utils.players_data has data, but config.players_data doesn't")
                print("🔧 This suggests the shared reference is broken")
            else:
                print("❌ utils.players_data is also empty - loading failed completely")
        else:
            print("✅ players_data has data after loading")
            
    except Exception as e:
        print(f"❌ Error in startup simulation: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Check the critical condition that's failing
    print("\n5️⃣ Testing the critical condition...")
    try:
        from config import players_data
        if not players_data:
            print("❌ CRITICAL CONDITION FAILS: 'if not players_data:' would be True")
            print("   This is why users see 'Player database is not available'")
        else:
            print("✅ CRITICAL CONDITION PASSES: 'if not players_data:' would be False")
            print("   Users should NOT see the error message")
    except Exception as e:
        print(f"❌ Error testing critical condition: {e}")

if __name__ == "__main__":
    test_production_debug()
