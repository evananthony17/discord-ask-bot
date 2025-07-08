from player_matching import has_multi_player_keywords, process_multi_player_query_fixed
from utils import load_players_from_json, normalize_name
from config import players_data

print("=== FINAL VERIFICATION TEST ===")

# Load the player data
loaded_players = load_players_from_json("players.json")
players_data.clear()
players_data.extend(loaded_players)
print(f"Loaded {len(players_data)} players")

# Test the exact query from the logs
query = "How are Suarez and Chapman doing"
print(f"\nTesting: '{query}'")

# Test 1: Keyword detection
has_keywords = has_multi_player_keywords(query)
print(f"1. Has multi-player keywords: {has_keywords}")

# Test 2: Full multi-player processing
try:
    should_allow, detected_players = process_multi_player_query_fixed(query)
    print(f"2. Multi-player processing result:")
    print(f"   Should allow: {should_allow}")
    print(f"   Detected players: {len(detected_players) if detected_players else 0}")
    
    if detected_players:
        print("   Players found:")
        for player in detected_players:
            print(f"     - {player['name']} ({player['team']})")
        
        # Check last names
        last_names = set()
        for player in detected_players:
            last_name = normalize_name(player['name']).split()[-1]
            last_names.add(last_name)
        
        print(f"   Unique last names: {list(last_names)} (count: {len(last_names)})")
    
    print(f"\n🎯 FINAL RESULT:")
    if should_allow:
        print("   ❌ QUERY WOULD BE ALLOWED (this is wrong)")
    else:
        print("   ✅ QUERY WOULD BE BLOCKED (this is correct)")
        
except Exception as e:
    print(f"   ERROR: {e}")

print(f"\n🔧 EXPECTED BEHAVIOR:")
print(f"   - Should find both Suarez and Chapman players")
print(f"   - Should detect multiple different last names")
print(f"   - Should detect multi-player keywords ('and')")
print(f"   - Should BLOCK the query as true multi-player")
