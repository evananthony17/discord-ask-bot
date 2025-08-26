#!/usr/bin/env python3
"""
Test the actual fix as implemented in bot.py
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

def test_actual_fix():
    """Test the actual fix as implemented in bot.py"""
    print("🧪 Testing actual fix implementation...")
    
    # Step 1: Import modules (like bot.py does)
    print("\n1️⃣ Importing modules (like bot.py does)...")
    from config import players_data as bot_players_data
    import player_matching
    from utils import load_players_from_json
    import utils
    
    print(f"📊 Initial bot_players_data: {len(bot_players_data)}")
    print(f"📊 Initial player_matching.players_data: {len(player_matching.players_data)}")
    print(f"📊 Initial utils.players_data: {len(utils.players_data)}")
    
    # Step 2: Simulate on_ready() - Load players (like bot.py does)
    print("\n2️⃣ Simulating on_ready() - Loading players...")
    players_loaded = load_players_from_json("players.json")
    print(f"📊 Players loaded from JSON: {len(players_loaded)}")
    print(f"📊 After loading - bot_players_data: {len(bot_players_data)}")
    print(f"📊 After loading - player_matching.players_data: {len(player_matching.players_data)}")
    print(f"📊 After loading - utils.players_data: {len(utils.players_data)}")
    
    # Step 3: Simulate the actual bot.py fix (verification only, no clearing)
    print("\n3️⃣ Simulating actual bot.py fix (verification only)...")
    print(f"📊 Verifying bot_players_data: {len(bot_players_data)} players")
    print(f"📊 Verifying utils.players_data: {len(utils.players_data)} players")
    print(f"📊 Verifying player_matching.players_data: {len(player_matching.players_data)} players")
    
    # Check if all modules have the same data
    all_have_same_data = (
        len(bot_players_data) == len(players_loaded) and
        len(utils.players_data) == len(players_loaded) and
        len(player_matching.players_data) == len(players_loaded)
    )
    
    if all_have_same_data:
        print("✅ All modules have the same player data - shared list working correctly")
    else:
        print("❌ Modules have different player data - shared list not working")
    
    # Step 4: Test the critical check
    print("\n4️⃣ Testing the critical 'if not players_data:' check...")
    if not bot_players_data:
        print("❌ CRITICAL CHECK: Would show 'Player database not available' error")
        critical_check_pass = False
    else:
        print("✅ CRITICAL CHECK: Would pass - no error message")
        critical_check_pass = True
    
    # Step 5: Test player detection
    print("\n5️⃣ Testing player detection...")
    try:
        test_question = "How good is Juan Soto?"
        matched_players = player_matching.check_player_mentioned(test_question)
        
        if matched_players and matched_players != "BLOCKED":
            print(f"✅ Player detection: Found {len(matched_players)} players")
            print(f"   Players: {[p['name'] for p in matched_players]}")
            player_detection_works = True
        elif matched_players == "BLOCKED":
            print("⚠️  Player detection: Returned BLOCKED (valid response)")
            player_detection_works = True
        else:
            print("❌ Player detection: No players found")
            player_detection_works = False
    except Exception as e:
        print(f"❌ Player detection: Error - {e}")
        player_detection_works = False
    
    # Final assessment
    print("\n📋 FINAL ASSESSMENT:")
    print(f"   Players loaded: {len(players_loaded)}")
    print(f"   All modules have data: {'✅ YES' if all_have_same_data else '❌ NO'}")
    print(f"   Critical check: {'✅ PASS' if critical_check_pass else '❌ FAIL'}")
    print(f"   Player detection: {'✅ WORKS' if player_detection_works else '❌ FAILED'}")
    
    overall_success = (
        len(players_loaded) > 0 and
        all_have_same_data and
        critical_check_pass
    )
    
    if overall_success:
        print("\n🎉 ACTUAL FIX TEST: SUCCESS!")
        print("   The 'Player database not available' error should be fixed")
        print("   The bot should work correctly with shared player data")
        return True
    else:
        print("\n💥 ACTUAL FIX TEST: FAILED!")
        return False

if __name__ == "__main__":
    success = test_actual_fix()
    sys.exit(0 if success else 1)
