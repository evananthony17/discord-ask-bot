from player_matching import process_multi_player_query_fixed, has_multi_player_keywords
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

print("\n=== TESTING MULTI-PLAYER LOGIC ===")
query = "Projections on Suarez and Chapman"

print(f"Query: '{query}'")

# Test the multi-player processing logic
print("\n1. Testing multi-player keyword detection:")
has_keywords = has_multi_player_keywords(query)
print(f"   Has multi-player keywords: {has_keywords}")

print("\n2. Testing multi-player query processing:")
try:
    should_allow, detected_players = process_multi_player_query_fixed(query)
    print(f"   Should allow query: {should_allow}")
    print(f"   Detected players: {len(detected_players) if detected_players else 0}")
    
    if detected_players:
        print("   Players found:")
        for player in detected_players:
            print(f"     - {player['name']} ({player['team']})")
        
        # Check last names
        last_names = set()
        for player in detected_players:
            player_name = player.get('name', '')
            from utils import normalize_name
            name_parts = normalize_name(player_name).lower().split()
            if name_parts:
                last_names.add(name_parts[-1])
        
        print(f"   Unique last names: {list(last_names)} (count: {len(last_names)})")
        
        if len(last_names) > 1:
            print(f"   Multiple last names detected - should check keywords")
            if has_keywords:
                print(f"   Has keywords + multiple last names = SHOULD BLOCK")
            else:
                print(f"   No keywords + multiple last names = SHOULD ALLOW")
        else:
            print(f"   Same last name - should allow for disambiguation")
    
except Exception as e:
    print(f"   Error: {e}")
