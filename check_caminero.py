#!/usr/bin/env python3
"""
Check for Caminero players in the database.
"""

import sys
import os

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import load_players_from_json

def check_caminero():
    """Check for Caminero players"""
    
    print("Loading players data...")
    players = load_players_from_json("players.json")
    print(f"Loaded {len(players)} players")
    
    # Search for Caminero
    caminero_players = [p for p in players if 'caminero' in p['name'].lower()]
    
    print(f"\nFound {len(caminero_players)} Caminero players:")
    for player in caminero_players:
        print(f"  - {player['name']} ({player['team']})")
    
    # Also check for partial matches
    print(f"\nChecking for partial 'camin' matches:")
    camin_players = [p for p in players if 'camin' in p['name'].lower()]
    for player in camin_players:
        print(f"  - {player['name']} ({player['team']})")

if __name__ == "__main__":
    check_caminero()
