from utils import load_players_from_json
from config import players_data

players = load_players_from_json('players.json')
suarez_players = [p for p in players if 'suarez' in p['name'].lower()]

print('All Suarez players in database:')
for p in suarez_players:
    print(f'  - {p["name"]} ({p["team"]})')

print(f'\nTotal Suarez players: {len(suarez_players)}')

# Check if any have Luis as first name
luis_suarez = [p for p in suarez_players if 'luis' in p['name'].lower()]
print(f'\nLuis Suarez players: {len(luis_suarez)}')
for p in luis_suarez:
    print(f'  - {p["name"]} ({p["team"]})')

# Check what happens when we search for "luis suarez"
print(f'\n=== Testing "luis suarez" detection ===')
from player_matching import simplified_fuzzy_match
matches = simplified_fuzzy_match('luis suarez')
print(f'Fuzzy matches for "luis suarez": {len(matches)}')
for match in matches:
    print(f'  - {match["name"]} ({match["team"]})')
