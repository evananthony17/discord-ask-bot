#!/usr/bin/env python3
"""
Test script to verify the player loading fix works correctly
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

def test_player_loading():
    """Test that player data loads correctly"""
    print("🧪 Testing player loading fix...")
    
    # Import modules
    from config import players_data as config_players_data
    from utils import load_players_from_json
    import utils
    
    print(f"📊 Initial config.players_data length: {len(config_players_data)}")
    print(f"📊 Initial utils.players_data length: {len(utils.players_data)}")
    
    # Load players (this should update utils.players_data)
    players_loaded = load_players_from_json("players.json")
    print(f"📊 Players loaded from JSON: {len(players_loaded)}")
    
    print(f"📊 After loading - config.players_data length: {len(config_players_data)}")
    print(f"📊 After loading - utils.players_data length: {len(utils.players_data)}")
    
    # Simulate the bot.py fix
    print("\n🔧 Simulating bot.py fix...")
    bot_players_data = []  # This simulates the imported players_data in bot.py
    
    # Original broken approach (what was happening before)
    print("❌ Broken approach:")
    bot_players_data.clear()
    bot_players_data.extend(config_players_data)  # This would still be empty
    print(f"📊 bot_players_data length (broken): {len(bot_players_data)}")
    
    # Fixed approach (what we implemented)
    print("✅ Fixed approach:")
    bot_players_data.clear()
    bot_players_data.extend(utils.players_data)  # This should have the loaded data
    print(f"📊 bot_players_data length (fixed): {len(bot_players_data)}")
    
    # Verify the fix works
    if len(bot_players_data) > 0:
        print(f"✅ SUCCESS: Player loading fix works! {len(bot_players_data)} players loaded")
        print(f"📝 Sample player: {bot_players_data[0]}")
        return True
    else:
        print("❌ FAILED: Player loading fix did not work")
        return False

if __name__ == "__main__":
    success = test_player_loading()
    if success:
        print("\n🎉 Player loading fix is working correctly!")
        sys.exit(0)
    else:
        print("\n💥 Player loading fix failed!")
        sys.exit(1)
