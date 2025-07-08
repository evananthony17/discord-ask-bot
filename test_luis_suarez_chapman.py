from player_matching import has_multi_player_keywords, process_multi_player_query_fixed, simplified_player_detection
from utils import load_players_from_json, normalize_name
from config import players_data

print("=== TESTING EXACT FAILING QUERY ===")

# Load the player data
loaded_players = load_players_from_json("players.json")
players_data.clear()
players_data.extend(loaded_players)
print(f"Loaded {len(players_data)} players")

# Test the exact failing query
query = "How are Luis Suarez and Chapman looking?"
print(f"\nTesting: '{query}'")

# Test 1: Keyword detection
has_keywords = has_multi_player_keywords(query)
print(f"1. Has multi-player keywords: {has_keywords}")

# Test 2: Early multi-player processing
print(f"2. Early multi-player processing:")
try:
    should_allow, detected_players = process_multi_player_query_fixed(query)
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
    
    if should_allow:
        print("   ❌ EARLY DETECTION ALLOWS (this is the problem)")
    else:
        print("   ✅ EARLY DETECTION BLOCKS")
        
except Exception as e:
    print(f"   ERROR: {e}")

# Test 3: Normal detection (what happens if early detection allows)
print(f"\n3. Normal detection (fallback path):")
try:
    normal_result = simplified_player_detection(query)
    if normal_result:
        if isinstance(normal_result, list):
            print(f"   Found {len(normal_result)} players:")
            for player in normal_result:
                print(f"     - {player['name']} ({player['team']})")
            
            # Check last names for normal detection
            last_names = set()
            for player in normal_result:
                last_name = normalize_name(player['name']).split()[-1]
                last_names.add(last_name)
            
            print(f"   Unique last names: {list(last_names)} (count: {len(last_names)})")
            
            if len(last_names) == 1:
                print("   → SAME LAST NAME: Would go to disambiguation")
            else:
                print("   → DIFFERENT LAST NAMES: Should be blocked as multi-player")
        else:
            print(f"   Found 1 player: {normal_result['name']} ({normal_result['team']})")
    else:
        print("   No players found")
except Exception as e:
    print(f"   ERROR: {e}")

print(f"\n🔧 ANALYSIS:")
print(f"   The bot showed Chapman disambiguation, which means:")
print(f"   1. Early detection ALLOWED the query (didn't block)")
print(f"   2. Normal detection found only Chapman players (missed Luis Suarez)")
print(f"   3. Same last name logic triggered disambiguation")
print(f"   4. This is wrong - should be blocked as multi-player")

print(f"\n🚨 EXPECTED BEHAVIOR:")
print(f"   - Should find Luis Suarez players AND Chapman players")
print(f"   - Should detect different last names (suarez + chapman)")
print(f"   - Should detect multi-player keywords ('and')")
print(f"   - Should BLOCK the query as true multi-player")
