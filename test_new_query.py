from player_matching import has_multi_player_keywords, process_multi_player_query_fixed
from utils import load_players_from_json
from config import players_data

print("=== LOADING PLAYER DATA ===")
# Load the player data like the bot does
loaded_players = load_players_from_json("players.json")
print(f"Loaded {len(loaded_players)} players from players.json")

# Update the global players_data
players_data.clear()
players_data.extend(loaded_players)
print(f"Updated global players_data: {len(players_data)} players")

print("\n=== TESTING NEW QUERY ===")
query = "How are Suarez and Chapman doing"

print(f"Query: '{query}'")

# Test 1: Multi-player keyword detection
has_keywords = has_multi_player_keywords(query)
print(f"1. Has multi-player keywords: {has_keywords}")

# Test 2: Multi-player processing
print(f"2. Testing multi-player query processing:")
try:
    should_allow, detected_players = process_multi_player_query_fixed(query)
    print(f"   Should allow query: {should_allow}")
    print(f"   Detected players: {len(detected_players) if detected_players else 0}")
    
    if detected_players:
        print("   Players found:")
        for player in detected_players:
            print(f"     - {player['name']} ({player['team']})")
    
    if not should_allow:
        print("   ✅ SHOULD BE BLOCKED")
    else:
        print("   ❌ SHOULD BE ALLOWED (this is the problem)")
        
except Exception as e:
    print(f"   Error: {e}")
    print("   This might be the routing issue!")
