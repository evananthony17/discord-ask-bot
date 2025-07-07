from player_matching import check_player_mentioned
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

print("\n=== TESTING TEAM FILTERING IN MAIN FLOW ===")
test_queries = [
    "Soto (Yankees) vs Harper (Phillies)",
    "Judge (Yankees) stats",
    "How is Ohtani (Angels) doing?",
    "Yankees vs Phillies",
    "Soto;Harper;Trout"
]

for query in test_queries:
    print(f"\nQuery: '{query}'")
    result = check_player_mentioned(query)
    if result:
        if isinstance(result, list):
            print(f"Found {len(result)} players: {[p['name'] for p in result]}")
        else:
            print(f"Found 1 player: {result['name']}")
    else:
        print("No players found")
