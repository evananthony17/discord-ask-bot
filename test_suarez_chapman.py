from player_matching import has_multi_player_keywords, simplified_player_detection, extract_potential_names
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

print("\n=== TESTING 'Projections on Suarez and Chapman' ===")
query = "Projections on Suarez and Chapman"

print(f"Query: '{query}'")

# Test 1: Multi-player keyword detection
has_keywords = has_multi_player_keywords(query)
print(f"Has multi-player keywords: {has_keywords}")

# Test 2: Name extraction
potential_names = extract_potential_names(query)
print(f"Extracted potential names: {potential_names}")

# Test 3: Full detection
try:
    result = simplified_player_detection(query)
    if result:
        if isinstance(result, list):
            print(f"Detection result: {len(result)} players found")
            for player in result:
                print(f"  - {player['name']} ({player['team']})")
        else:
            print(f"Detection result: 1 player found - {result['name']} ({result['team']})")
    else:
        print("Detection result: No players found")
except Exception as e:
    print(f"Detection error: {e}")
