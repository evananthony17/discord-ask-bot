from player_matching import simplified_player_detection
from utils import is_likely_player_request, load_players_from_json
from config import players_data

print("=== LOADING PLAYER DATA ===")
# Load the player data like the bot does
loaded_players = load_players_from_json("players.json")
print(f"Loaded {len(loaded_players)} players from players.json")

# Update the global players_data
players_data.clear()
players_data.extend(loaded_players)
print(f"Updated global players_data: {len(players_data)} players")

print("\n=== TESTING QUERY ===")
query = 'Juan Soto stats'
print(f"Testing query: '{query}'")
print(f"is_likely_player_request: {is_likely_player_request(query)}")

if players_data:
    # Check if Juan Soto is in the data
    juan_sotos = [p for p in players_data if 'soto' in p['name'].lower() and 'juan' in p['name'].lower()]
    print(f"Juan Soto players found: {[p['name'] for p in juan_sotos]}")

print("\n=== RUNNING SIMPLIFIED DETECTION ===")
result = simplified_player_detection(query)
print(f'Result: {result}')
if result:
    if isinstance(result, list):
        print(f'Found: {[p["name"] for p in result]}')
    else:
        print(f'Found: {result["name"]}')
else:
    print('Found: None')
