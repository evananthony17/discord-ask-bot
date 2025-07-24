#!/usr/bin/env python3

"""
Test the Victor Scott → Victor Scott II suffix-aware matching fix
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_suffix_aware_matching():
    """Test that Victor Scott matches Victor Scott II"""
    print("=" * 70)
    print("TESTING SUFFIX-AWARE MATCHING")
    print("=" * 70)
    
    try:
        from player_matching import simplified_fuzzy_match
        
        # Test cases for suffix matching
        test_cases = [
            {
                'query': 'victor scott',
                'expected_player': 'Victor Scott II',
                'description': 'Victor Scott should match Victor Scott II'
            },
            {
                'query': 'cal ripken',
                'expected_player': 'Cal Ripken Jr',
                'description': 'Cal Ripken should match Cal Ripken Jr (if exists)'
            },
            {
                'query': 'ken griffey',
                'expected_player': 'Ken Griffey Jr',
                'description': 'Ken Griffey should match Ken Griffey Jr (if exists)'
            }
        ]
        
        # Load players data
        from config import players_data
        from utils import load_players_from_json
        
        if not players_data:
            print("Loading players data...")
            loaded_players = load_players_from_json("players.json")
            players_data.clear()
            players_data.extend(loaded_players)
            print(f"Loaded {len(players_data)} players")
        
        # Find Victor Scott II in the database
        victor_scott_players = [p for p in players_data if 'victor scott' in p['name'].lower()]
        print(f"Found Victor Scott players: {[p['name'] for p in victor_scott_players]}")
        
        passed = 0
        for i, case in enumerate(test_cases):
            print(f"\nTEST {i+1}: {case['description']}")
            print(f"Query: '{case['query']}'")
            
            # Test the simplified fuzzy matching
            matches = simplified_fuzzy_match(case['query'], max_results=5)
            
            if matches:
                print(f"Found {len(matches)} matches:")
                for match in matches:
                    print(f"  - {match['name']} ({match['team']})")
                
                # Check if expected player is in matches
                expected_found = any(case['expected_player'].lower() in match['name'].lower() 
                                   for match in matches)
                
                if expected_found:
                    print(f"✅ SUCCESS: Found expected player containing '{case['expected_player']}'")
                    passed += 1
                else:
                    print(f"❌ FAILED: Expected player '{case['expected_player']}' not found")
                    # Check if any similar players exist
                    similar_players = [p for p in players_data 
                                     if case['expected_player'].lower() in p['name'].lower()]
                    if similar_players:
                        print(f"   Similar players in database: {[p['name'] for p in similar_players]}")
                    else:
                        print(f"   No players containing '{case['expected_player']}' found in database")
            else:
                print(f"❌ FAILED: No matches found for '{case['query']}'")
        
        print(f"\nSuffix matching test: {passed}/{len(test_cases)} passed")
        return passed == len(test_cases)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_integration_victor_scott():
    """Test the full integration with Victor Scott"""
    print("\n" + "=" * 70)
    print("TESTING FULL INTEGRATION - VICTOR SCOTT")
    print("=" * 70)
    
    try:
        from player_matching import check_player_mentioned
        
        # Test the exact query from the log
        query = "what are the impacts of fielding and base running for Victor Scott ? He even hit a home run this week!"
        
        print(f"Testing query: '{query}'")
        
        result = check_player_mentioned(query)
        
        if result and result != "BLOCKED":
            if isinstance(result, list):
                print(f"✅ SUCCESS: Found {len(result)} players:")
                for player in result:
                    print(f"  - {player['name']} ({player['team']})")
                
                # Check if Victor Scott II is in the results
                victor_found = any('victor scott' in player['name'].lower() for player in result)
                if victor_found:
                    print(f"✅ EXCELLENT: Victor Scott found in results!")
                    return True
                else:
                    print(f"⚠️  PARTIAL: Players found but no Victor Scott")
                    return False
            else:
                print(f"✅ SUCCESS: Found single player: {result['name']} ({result['team']})")
                victor_found = 'victor scott' in result['name'].lower()
                if victor_found:
                    print(f"✅ EXCELLENT: Victor Scott found!")
                    return True
                else:
                    print(f"⚠️  PARTIAL: Different player found")
                    return False
        elif result == "BLOCKED":
            print(f"❌ FAILED: Query was blocked (should not be blocked)")
            return False
        else:
            print(f"❌ FAILED: No players found")
            return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all Victor Scott tests"""
    print("🔧 VICTOR SCOTT SUFFIX MATCHING TEST")
    print("Testing the enhanced fuzzy matching with suffix-aware logic")
    print()
    
    test1_passed = test_suffix_aware_matching()
    test2_passed = test_full_integration_victor_scott()
    
    print("\n" + "=" * 70)
    print("VICTOR SCOTT TEST RESULTS")
    print("=" * 70)
    
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Suffix-aware matching is working")
        print("✅ Victor Scott integration is working")
        print("\n🚀 The Victor Scott → Victor Scott II issue is FIXED!")
        return True
    else:
        print("❌ SOME TESTS FAILED!")
        if not test1_passed:
            print("❌ Suffix-aware matching issue")
        if not test2_passed:
            print("❌ Integration issue")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
