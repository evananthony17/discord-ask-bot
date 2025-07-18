#!/usr/bin/env python3
"""
Test script to verify the Alex Vesia name extraction fix.
"""

import sys
import os

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import load_players_from_json
from player_matching import extract_potential_names, simplified_player_detection

def test_alex_vesia_fix():
    """Test the Alex Vesia name extraction fix"""
    
    print("Loading players data...")
    loaded_players = load_players_from_json("players.json")
    print(f"Loaded {len(loaded_players)} players")
    
    test_query = "what is the outlook on Alex Vesia does he have a shot at 82"
    print(f"\nTesting query: '{test_query}'")
    print("=" * 80)
    
    # Test the name extraction directly
    print("Step 1: Testing name extraction...")
    potential_names = extract_potential_names(test_query)
    print(f"Extracted potential names: {potential_names}")
    
    # Check if "alex vesia" is in the extracted names
    alex_vesia_found = any('alex vesia' in name.lower() for name in potential_names)
    if alex_vesia_found:
        print("✅ SUCCESS: 'Alex Vesia' found in extracted names")
    else:
        print("❌ FAILURE: 'Alex Vesia' not found in extracted names")
        print("   Expected to find 'alex vesia' as a 2-word combination")
    
    # Test the full player detection
    print("\nStep 2: Testing full player detection...")
    try:
        result = simplified_player_detection(test_query)
        
        if result:
            if isinstance(result, list):
                print(f"✅ SUCCESS: Found {len(result)} players:")
                for player in result:
                    print(f"  - {player['name']} ({player['team']})")
                
                # Check if Alex Vesia is in the results
                alex_vesia_found = any('alex vesia' in player['name'].lower() for player in result)
                if alex_vesia_found:
                    print("✅ PERFECT: Alex Vesia found in results as expected")
                else:
                    print("⚠️  PARTIAL: Results found but Alex Vesia not among them")
            else:
                print(f"✅ SUCCESS: Found single player: {result['name']} ({result['team']})")
                if 'alex vesia' in result['name'].lower():
                    print("✅ PERFECT: Alex Vesia found as expected")
                else:
                    print("⚠️  PARTIAL: Different player found")
        else:
            print("❌ FAILURE: No players found - Alex Vesia should have been detected")
    except Exception as e:
        print(f"❌ ERROR: Exception during player detection: {e}")

    # Test a few more similar cases
    print("\n" + "=" * 80)
    print("Testing additional 2-word name cases:")
    
    additional_tests = [
        "how is Juan Soto doing this season?",
        "what about Mike Trout's performance lately?", 
        "tell me about Shohei Ohtani's pitching",
        "any updates on Ronald Acuna?"
    ]
    
    for test_case in additional_tests:
        print(f"\nTesting: '{test_case}'")
        potential_names = extract_potential_names(test_case)
        
        # Look for 2-word combinations
        two_word_names = [name for name in potential_names if len(name.split()) == 2]
        if two_word_names:
            print(f"✅ Found 2-word names: {two_word_names}")
        else:
            print("⚠️  No 2-word names extracted")

if __name__ == "__main__":
    test_alex_vesia_fix()
