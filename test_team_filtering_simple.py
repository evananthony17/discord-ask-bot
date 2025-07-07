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

print("\n=== TESTING TEAM FILTERING ===")
test_queries = [
    "Soto (Yankees) vs Harper (Phillies)",
    "Judge (Yankees) stats", 
    "Yankees vs Phillies",
    "Soto;Harper;Yankees;Phillies"
]

for query in test_queries:
    print(f"\nQuery: '{query}'")
    potential_names = extract_potential_names(query)
    print(f"Extracted names: {potential_names}")
    
    # Check if team names were filtered out
    team_names = ['yankees', 'phillies', 'angels', 'dodgers', 'mets']
    teams_found = [name for name in potential_names if name.lower() in team_names]
    if teams_found:
        print(f"❌ TEAM FILTERING FAILED: Found team names: {teams_found}")
    else:
        print(f"✅ TEAM FILTERING WORKING: No team names in results")
