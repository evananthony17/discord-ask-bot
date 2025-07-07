from player_matching import simplified_player_detection, extract_potential_names
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

print("\n=== TESTING DIAZ QUERY ===")
query = 'Diaz stats?'
print(f"Testing query: '{query}'")

print("\n=== NAME EXTRACTION TEST ===")
potential_names = extract_potential_names(query)
print(f"Extracted potential names: {potential_names}")

print("\n=== RUNNING SIMPLIFIED DETECTION ===")
result = simplified_player_detection(query)
print(f'Result: {result}')
if result:
    if isinstance(result, list):
        print(f'Found: {[p["name"] for p in result]}')
        print(f'Count: {len(result)} players')
    else:
        print(f'Found: {result["name"]}')
else:
    print('Found: None')

print("\n=== CHECKING FOR DIAZ PLAYERS ===")
diaz_players = [p for p in players_data if 'diaz' in p['name'].lower()]
print(f"Diaz players in database: {[p['name'] for p in diaz_players]}")
