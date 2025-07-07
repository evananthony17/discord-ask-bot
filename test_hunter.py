from player_matching import simplified_player_detection, has_multi_player_keywords
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

print("\n=== TESTING HUNTER QUERY ===")
query = 'How is Hunter looking'
print(f"Testing query: '{query}'")

# Test multi-player keywords detection
has_keywords = has_multi_player_keywords(query)
print(f"has_multi_player_keywords: {has_keywords}")

print("\n=== RUNNING SIMPLIFIED DETECTION ===")
result = simplified_player_detection(query)
print(f'Result: {result}')
if result:
    if isinstance(result, list):
        print(f'Found: {[p["name"] for p in result]}')
        print(f'Count: {len(result)} players')
        
        # Check last names
        last_names = set()
        for player in result:
            name_parts = player['name'].split()
            if name_parts:
                last_names.add(name_parts[-1])
        print(f'Unique last names: {list(last_names)} (count: {len(last_names)})')
    else:
        print(f'Found: {result["name"]}')
else:
    print('Found: None')
