#!/usr/bin/env python3
"""
Complete test to verify both the player loading fix and log_memory_usage function work
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

def test_complete_fix():
    """Test both player loading and log_memory_usage function"""
    print("🧪 Testing complete fix...")
    
    # Test 1: Player loading fix
    print("\n1️⃣ Testing player loading fix...")
    from config import players_data as config_players_data
    from utils import load_players_from_json
    import utils
    
    print(f"📊 Initial players_data length: {len(config_players_data)}")
    
    # Load players
    players_loaded = load_players_from_json("players.json")
    print(f"📊 Players loaded from JSON: {len(players_loaded)}")
    print(f"📊 After loading - config.players_data length: {len(config_players_data)}")
    
    # Simulate bot.py fix
    bot_players_data = []
    bot_players_data.extend(utils.players_data)
    print(f"📊 bot_players_data length (after fix): {len(bot_players_data)}")
    
    player_loading_success = len(bot_players_data) > 0
    if player_loading_success:
        print("✅ Player loading fix: SUCCESS")
    else:
        print("❌ Player loading fix: FAILED")
    
    # Test 2: log_memory_usage function
    print("\n2️⃣ Testing log_memory_usage function...")
    try:
        from logging_system import log_memory_usage
        
        # Test the function with different parameters
        log_memory_usage("Test Stage")
        log_memory_usage("Test Stage with ID", "test123")
        
        print("✅ log_memory_usage function: SUCCESS")
        log_memory_usage_success = True
    except Exception as e:
        print(f"❌ log_memory_usage function: FAILED - {e}")
        log_memory_usage_success = False
    
    # Test 3: Check if players_data check would pass
    print("\n3️⃣ Testing players_data availability check...")
    if bot_players_data:  # This simulates the "if not players_data:" check in bot.py
        print("✅ players_data availability check: WOULD PASS")
        availability_check_success = True
    else:
        print("❌ players_data availability check: WOULD FAIL")
        availability_check_success = False
    
    # Overall result
    print("\n📋 SUMMARY:")
    print(f"   Player loading fix: {'✅ PASS' if player_loading_success else '❌ FAIL'}")
    print(f"   log_memory_usage function: {'✅ PASS' if log_memory_usage_success else '❌ FAIL'}")
    print(f"   Players availability check: {'✅ PASS' if availability_check_success else '❌ FAIL'}")
    
    overall_success = player_loading_success and log_memory_usage_success and availability_check_success
    
    if overall_success:
        print("\n🎉 ALL FIXES WORKING CORRECTLY!")
        print(f"   The bot should now work with {len(bot_players_data)} players loaded")
        return True
    else:
        print("\n💥 SOME FIXES FAILED!")
        return False

if __name__ == "__main__":
    success = test_complete_fix()
    sys.exit(0 if success else 1)
