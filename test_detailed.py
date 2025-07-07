from player_matching import simplified_player_detection
from utils import is_likely_player_request
from config import players_data

print("=== DETAILED TEST ===")
query = 'Juan Soto stats'
print(f"Testing query: '{query}'")

print(f"Players data loaded: {len(players_data) if players_data else 0} players")
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
