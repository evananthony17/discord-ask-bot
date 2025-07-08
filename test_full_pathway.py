import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.getcwd())

from player_matching import has_multi_player_keywords, process_multi_player_query_fixed, simplified_player_detection
from bot_logic import handle_multi_player_question
from utils import load_players_from_json, normalize_name
from config import players_data

print("=== LOADING PLAYER DATA ===")
# Load the player data like the bot does
loaded_players = load_players_from_json("players.json")
print(f"Loaded {len(loaded_players)} players from players.json")

# Update the global players_data
players_data.clear()
players_data.extend(loaded_players)
print(f"Updated global players_data: {len(players_data)} players")

print("\n=== TESTING FULL PATHWAY ===")
query = "How are Suarez and Chapman doing"

print(f"Query: '{query}'")
print()

# Test 1: Multi-player keyword detection
print("1. TESTING: has_multi_player_keywords()")
has_keywords = has_multi_player_keywords(query)
print(f"   Result: {has_keywords}")
print()

# Test 2: Early multi-player processing (what bot.py calls first)
print("2. TESTING: process_multi_player_query_fixed() - Early Detection")
try:
    should_allow, detected_players = process_multi_player_query_fixed(query)
    print(f"   Should allow: {should_allow}")
    print(f"   Detected players: {len(detected_players) if detected_players else 0}")
    if detected_players:
        print("   Players:")
        for player in detected_players:
            print(f"     - {player['name']} ({player['team']})")
    print(f"   DECISION: {'ALLOW' if should_allow else 'BLOCK'}")
except Exception as e:
    print(f"   ERROR: {e}")
print()

# Test 3: Normal player detection (what bot.py calls if early detection passes)
print("3. TESTING: simplified_player_detection() - Normal Detection")
try:
    normal_result = simplified_player_detection(query)
    if normal_result:
        if isinstance(normal_result, list):
            print(f"   Found {len(normal_result)} players:")
            for player in normal_result:
                print(f"     - {player['name']} ({player['team']})")
        else:
            print(f"   Found 1 player: {normal_result['name']} ({normal_result['team']})")
    else:
        print("   No players found")
except Exception as e:
    print(f"   ERROR: {e}")
print()

# Test 4: Check what handle_multi_player_question would do
print("4. TESTING: bot_logic.handle_multi_player_question() logic")
if normal_result and isinstance(normal_result, list) and len(normal_result) > 1:
    print(f"   Multiple players detected: {len(normal_result)}")
    
    # Simulate the logic in handle_multi_player_question
    last_names = set()
    for player in normal_result:
        last_name = normalize_name(player['name']).split()[-1]
        last_names.add(last_name)
    
    print(f"   Unique last names: {list(last_names)} (count: {len(last_names)})")
    
    if len(last_names) > 1 and has_multi_player_keywords(query):
        print("   DECISION: BLOCK (multiple last names + keywords)")
    else:
        print("   DECISION: ALLOW for disambiguation")
else:
    print("   Not applicable (single or no players)")
print()

# Test 5: Check selection_handlers logic
print("5. TESTING: selection_handlers.handle_disambiguation_selection() logic")
if normal_result and isinstance(normal_result, list) and len(normal_result) > 1:
    print(f"   Simulating disambiguation selection...")
    
    # Simulate the logic in handle_disambiguation_selection
    multi_player_indicators = ['and', '&', ',', 'both', 'all', 'compare', 'vs', 'versus']
    question_lower = query.lower()
    
    has_indicators = any(indicator in question_lower for indicator in multi_player_indicators)
    print(f"   Has multi-player indicators: {has_indicators}")
    
    if has_indicators:
        last_names = set()
        for player in normal_result:
            last_name = normalize_name(player['name']).split()[-1]
            last_names.add(last_name)
        
        print(f"   Unique last names: {list(last_names)} (count: {len(last_names)})")
        
        if len(last_names) > 1:
            print("   DECISION: BLOCK after disambiguation (multiple last names + indicators)")
        else:
            print("   DECISION: ALLOW (same last name)")
    else:
        print("   DECISION: ALLOW (no indicators)")
else:
    print("   Not applicable (single or no players)")

print("\n=== PATHWAY ANALYSIS ===")
print("The bot follows this pathway:")
print("1. Early detection: process_multi_player_query_fixed()")
print("2. If allowed, normal detection: simplified_player_detection()")
print("3. If multiple players, bot_logic.handle_multi_player_question()")
print("4. If disambiguation shown, selection_handlers.handle_disambiguation_selection()")
print()
print("🚨 POTENTIAL ISSUES:")
print("- Multiple functions have their own multi-player logic")
print("- Each could override the previous decision")
print("- Need to ensure consistency across all functions")
