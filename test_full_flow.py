from player_matching import simplified_player_detection
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

print("\n=== TESTING FULL DETECTION FLOW ===")
test_queries = [
    "Soto;Edman;trout",
    "Judge,Ohtani,Harper",
    "Soto/Harper/Trout"
]

for query in test_queries:
    print(f"\nQuery: '{query}'")
    try:
        result = simplified_player_detection(query)
        if result:
            if isinstance(result, list):
                print(f"✅ SUCCESS: Found {len(result)} players: {[p['name'] for p in result]}")
            else:
                print(f"✅ SUCCESS: Found 1 player: {result['name']}")
        else:
            print("❌ FAILED: No players found")
    except Exception as e:
        print(f"❌ ERROR: {e}")
