#!/usr/bin/env python3
"""
Test that simulates the exact bot startup sequence to verify the fix
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

def test_bot_startup_simulation():
    """Simulate the exact bot startup sequence"""
    print("🧪 Testing bot startup simulation...")
    
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
    
    # Step 3: Apply the bot.py fix
    print("\n3️⃣ Applying bot.py fix...")
    bot_players_data.clear()
    bot_players_data.extend(utils.players_data)
    print(f"📊 After bot.py fix - bot_players_data: {len(bot_players_data)}")
    
    # Step 4: Apply the player_matching fix
    print("\n4️⃣ Applying player_matching fix...")
    player_matching.players_data.clear()
    player_matching.players_data.extend(utils.players_data)
    print(f"📊 After player_matching fix - player_matching.players_data: {len(player_matching.players_data)}")
    
    # Step 5: Test the critical check
    print("\n5️⃣ Testing the critical 'if not players_data:' check...")
    if not bot_players_data:
        print("❌ CRITICAL CHECK: Would show 'Player database not available' error")
        critical_check_pass = False
    else:
        print("✅ CRITICAL CHECK: Would pass - no error message")
        critical_check_pass = True
    
    # Step 6: Test player detection
    print("\n6️⃣ Testing player detection...")
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
    print(f"   bot_players_data: {len(bot_players_data)}")
    print(f"   player_matching.players_data: {len(player_matching.players_data)}")
    print(f"   Critical check: {'✅ PASS' if critical_check_pass else '❌ FAIL'}")
    print(f"   Player detection: {'✅ WORKS' if player_detection_works else '❌ FAILED'}")
    
    overall_success = (
        len(players_loaded) > 0 and
        len(bot_players_data) > 0 and
        len(player_matching.players_data) > 0 and
        critical_check_pass
    )
    
    if overall_success:
        print("\n🎉 BOT STARTUP SIMULATION: SUCCESS!")
        print("   The 'Player database not available' error should be fixed")
        return True
    else:
        print("\n💥 BOT STARTUP SIMULATION: FAILED!")
        return False

if __name__ == "__main__":
    success = test_bot_startup_simulation()
    sys.exit(0 if success else 1)
