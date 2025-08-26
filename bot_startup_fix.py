#!/usr/bin/env python3
"""
Comprehensive fix for the bot startup and player loading issue
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

def create_startup_fix():
    """Create a comprehensive fix for the bot startup issue"""
    
    # Read the current bot.py
    with open("bot.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Find the on_ready function and replace it with a more robust version
    on_ready_start = content.find("@bot.event\n@safe_discord_operation(\"bot_startup\")\nasync def on_ready():")
    if on_ready_start == -1:
        print("❌ Could not find on_ready function")
        return False
    
    # Find the end of the on_ready function (next @bot.event or end of file)
    on_ready_end = content.find("\n@bot.event", on_ready_start + 1)
    if on_ready_end == -1:
        # Look for the next function definition
        on_ready_end = content.find("\n@bot.command", on_ready_start + 1)
        if on_ready_end == -1:
            print("❌ Could not find end of on_ready function")
            return False
    
    # Extract everything before and after on_ready
    before_on_ready = content[:on_ready_start]
    after_on_ready = content[on_ready_end:]
    
    # Create the new robust on_ready function
    new_on_ready = '''@bot.event
@safe_discord_operation("bot_startup")
async def on_ready():
    """Enhanced startup with comprehensive error handling and verification"""
    try:
        print(f"✅ Bot logged in as {bot.user}")
        
        # CRITICAL: Start batching first
        start_batching()
        log_info("STARTUP: Log batching started")
        
        # CRITICAL: Load player data with comprehensive error handling
        log_info("STARTUP: Beginning player data loading...")
        
        try:
            # Load profanity words
            log_info("STARTUP: Loading profanity words...")
            profanity_words = load_words_from_json("profanity.json")
            banned_categories["profanity"]["words"] = profanity_words
            log_info(f"STARTUP: Loaded {len(profanity_words)} profanity words")
            
            # Load players with detailed logging
            log_info("STARTUP: Loading players from JSON...")
            players_loaded = load_players_from_json("players.json")
            log_info(f"STARTUP: load_players_from_json returned {len(players_loaded)} players")
            
            # CRITICAL: Verify the global players_data was updated
            log_info(f"STARTUP: Checking global players_data length: {len(players_data)}")
            
            if len(players_data) == 0:
                log_error("CRITICAL STARTUP ERROR: players_data is empty after loading!")
                log_error("STARTUP: Attempting emergency player data fix...")
                
                # Emergency fix: directly extend the global list
                players_data.extend(players_loaded)
                log_info(f"STARTUP: Emergency fix applied, players_data now has {len(players_data)} players")
            
            # Verify all modules have the data
            import utils
            import player_matching
            log_info(f"STARTUP: Verification - bot.py players_data: {len(players_data)}")
            log_info(f"STARTUP: Verification - utils.players_data: {len(utils.players_data)}")
            log_info(f"STARTUP: Verification - player_matching.players_data: {len(player_matching.players_data)}")
            
            # Check if they're the same object (they should be)
            log_info(f"STARTUP: Object identity check - same object: {players_data is utils.players_data}")
            
            if len(players_data) != len(players_loaded):
                log_error(f"STARTUP ERROR: Length mismatch - loaded {len(players_loaded)}, have {len(players_data)}")
            else:
                log_success(f"STARTUP: Successfully loaded {len(players_data)} players")
            
            # Load nicknames
            log_info("STARTUP: Loading nicknames...")
            load_nicknames_from_json("nicknames.json")
            log_info("STARTUP: Nicknames loaded successfully")
            
        except Exception as e:
            log_error(f"CRITICAL STARTUP ERROR in data loading: {e}")
            import traceback
            log_error(f"STARTUP ERROR TRACEBACK: {traceback.format_exc()}")
            # Don't return - continue with startup even if data loading fails
        
        # Analytics (with emergency mode check)
        try:
            if not EMERGENCY_MODE:
                await log_analytics("Bot Health", event="startup", bot_name=str(bot.user), 
                                    total_questions=0, blocked_questions=0, error_count=0)
                log_info("STARTUP: Analytics logged successfully")
            else:
                log_info("STARTUP: Skipping analytics due to emergency mode")
        except Exception as e:
            log_error(f"STARTUP: Analytics failed: {e}")
        
        # Final verification
        log_info("STARTUP: Performing final verification...")
        if len(players_data) > 0:
            log_success(f"STARTUP COMPLETE: Bot ready with {len(players_data)} players loaded")
            print(f"🎉 STARTUP SUCCESS: {len(players_data)} players loaded and verified")
        else:
            log_error("STARTUP WARNING: Bot started but no player data available")
            print("⚠️ STARTUP WARNING: No player data loaded")
        
        # Cleanup
        log_info("STARTUP: Cleaning up orphaned disambiguation messages")
        pending_selections.clear()
        
        log_success("Bot startup sequence completed!")
        
    except Exception as e:
        log_error(f"CRITICAL STARTUP FAILURE: {e}")
        import traceback
        log_error(f"STARTUP FAILURE TRACEBACK: {traceback.format_exc()}")
        print(f"💥 STARTUP FAILED: {e}")
        # Don't re-raise - let the bot continue even with startup issues'''
    
    # Combine the parts
    new_content = before_on_ready + new_on_ready + after_on_ready
    
    # Write the fixed version
    with open("bot.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print("✅ Created comprehensive startup fix")
    return True

def create_emergency_player_loader():
    """Create an emergency player loader that can be called from anywhere"""
    
    emergency_loader = '''
def emergency_load_players():
    """Emergency function to load players if startup failed"""
    try:
        from utils import load_players_from_json
        from config import players_data
        
        if len(players_data) == 0:
            print("🚨 EMERGENCY: Loading players due to empty players_data")
            players_loaded = load_players_from_json("players.json")
            
            if len(players_data) == 0 and len(players_loaded) > 0:
                # Direct extension as emergency measure
                players_data.extend(players_loaded)
                print(f"🚨 EMERGENCY: Loaded {len(players_data)} players")
                return True
            elif len(players_data) > 0:
                print(f"✅ EMERGENCY: players_data already has {len(players_data)} players")
                return True
            else:
                print("❌ EMERGENCY: Failed to load any players")
                return False
        else:
            print(f"✅ EMERGENCY: players_data already has {len(players_data)} players")
            return True
            
    except Exception as e:
        print(f"❌ EMERGENCY LOADER FAILED: {e}")
        return False
'''
    
    # Read current bot.py
    with open("bot.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Add the emergency loader before the ask_question command
    ask_command_pos = content.find("@bot.command(name=\"ask\")")
    if ask_command_pos == -1:
        print("❌ Could not find ask command")
        return False
    
    # Insert the emergency loader
    new_content = content[:ask_command_pos] + emergency_loader + "\n" + content[ask_command_pos:]
    
    # Also modify the ask command to use the emergency loader
    # Find the "if not players_data:" check
    check_pos = new_content.find("if not players_data:")
    if check_pos != -1:
        # Find the end of this if block
        block_end = new_content.find("return", check_pos)
        if block_end != -1:
            # Insert emergency loader call before the error
            before_check = new_content[:check_pos]
            after_return = new_content[block_end:]
            
            emergency_check = '''# EMERGENCY: Try to load players if they're missing
        if not players_data:
            logger.info(f"🚨 EMERGENCY [{request_id}]: players_data is empty, attempting emergency load")
            if emergency_load_players():
                logger.info(f"🚨 EMERGENCY [{request_id}]: Emergency load successful, continuing")
            else:
                logger.info(f"🚨 EMERGENCY [{request_id}]: Emergency load failed, showing error")
        
        if not players_data:'''
            
            new_content = before_check + emergency_check + after_return
    
    # Write the updated version
    with open("bot.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print("✅ Added emergency player loader")
    return True

if __name__ == "__main__":
    print("🔧 Creating comprehensive bot startup fix...")
    
    if create_startup_fix():
        print("✅ Startup fix created")
    else:
        print("❌ Failed to create startup fix")
        sys.exit(1)
    
    if create_emergency_player_loader():
        print("✅ Emergency loader added")
    else:
        print("❌ Failed to add emergency loader")
        sys.exit(1)
    
    print("🎉 Comprehensive fix complete!")
    print("\nThe fix includes:")
    print("1. Enhanced on_ready() with detailed logging and error handling")
    print("2. Emergency player loading if startup fails")
    print("3. Comprehensive verification of player data across all modules")
    print("4. Fallback mechanisms for production environment differences")
