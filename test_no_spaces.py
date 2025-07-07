from player_matching import extract_potential_names
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

print("\n=== TESTING NO SPACES PARSING ===")
test_queries = [
    "Soto;Harper;Trout",
    "Judge,Ohtani,Trout", 
    "Soto/Harper/Trout",
    "Judge&Ohtani&Trout",
    "Soto(Yankees)Harper(Phillies)"
]

for query in test_queries:
    print(f"\nQuery: '{query}'")
    potential_names = extract_potential_names(query)
    print(f"Extracted: {potential_names}")
