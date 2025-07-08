from player_matching import has_multi_player_keywords, simplified_player_detection
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

print("\n=== TESTING SIMPLE MULTI-PLAYER LOGIC ===")
query = "Projections on Suarez and Chapman"

print(f"Query: '{query}'")

# Test 1: Multi-player keyword detection
has_keywords = has_multi_player_keywords(query)
print(f"1. Has multi-player keywords: {has_keywords}")

# Test 2: Simulate the detection without asyncio
print(f"2. Simulating player detection...")

# Manually create some test players to simulate what would be detected
test_players = [
    {'name': 'Albert Suárez', 'team': 'Free Agents'},
    {'name': 'Eugenio Suárez', 'team': 'Diamondbacks'},
    {'name': 'José Suarez', 'team': 'Free Agents'},
    {'name': 'Aroldis Chapman', 'team': 'Red Sox'},
    {'name': 'Matt Chapman', 'team': 'Giants'}
]

print(f"   Simulated detected players: {len(test_players)}")
for player in test_players:
    print(f"     - {player['name']} ({player['team']})")

# Test 3: Check last names
last_names = set()
for player in test_players:
    player_name = player.get('name', '')
    name_parts = normalize_name(player_name).lower().split()
    if name_parts:
        last_names.add(name_parts[-1])

print(f"3. Unique last names: {list(last_names)} (count: {len(last_names)})")

# Test 4: Apply the multi-player blocking logic
if len(test_players) > 1:
    print(f"4. Multiple players detected")
    
    if len(last_names) > 1:
        print(f"   Multiple different last names detected")
        
        if has_keywords:
            print(f"   ✅ Has keywords + multiple last names = SHOULD BLOCK")
            should_block = True
        else:
            print(f"   ❌ No keywords + multiple last names = SHOULD ALLOW (disambiguation)")
            should_block = False
    else:
        print(f"   Same last name detected = SHOULD ALLOW (disambiguation)")
        should_block = False
else:
    print(f"4. Single or no players = SHOULD ALLOW")
    should_block = False

print(f"\n🎯 FINAL DECISION: {'BLOCK' if should_block else 'ALLOW'} the query")

if should_block:
    print("   This query should be blocked as multi-player")
else:
    print("   This query should be allowed (single player or disambiguation)")
