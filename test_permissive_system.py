#!/usr/bin/env python3

"""
Test the simplified, permissive multi-player detection system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_permissive_multi_player_detection():
    """Test that the simplified system is more permissive"""
    print("=" * 70)
    print("TESTING PERMISSIVE MULTI-PLAYER DETECTION")
    print("=" * 70)
    
    try:
        from player_matching import has_multi_player_keywords_enhanced
        
        # Test cases that should NOT be blocked (permissive)
        permissive_cases = [
            "should we bail on Okert or is it early enough that he can make up for tonight?",
            "Soto and Harper are both good",
            "What about Judge or Ohtani for tonight?",
            "I'm thinking Trout, but maybe Acuna instead",
            "Start Betts or sit him tonight?",
            "How is Tatis looking, or should I go with someone else?",
        ]
        
        # Test cases that SHOULD be blocked (obvious multi-player)
        blocking_cases = [
            "Soto vs Judge who is better",
            "Judge versus Ohtani comparison",
            "Player1;Player2;Player3;Player4;Player5",  # Need 4+ segments now
        ]
        
        print("Testing permissive cases (should NOT be blocked):")
        permissive_passed = 0
        for case in permissive_cases:
            has_intent, segments = has_multi_player_keywords_enhanced(case)
            if not has_intent:
                print(f"✅ GOOD: '{case}' was NOT blocked")
                permissive_passed += 1
            else:
                print(f"❌ BAD: '{case}' was incorrectly blocked")
        
        print(f"\nPermissive test: {permissive_passed}/{len(permissive_cases)} passed")
        
        print("\nTesting blocking cases (SHOULD be blocked):")
        blocking_passed = 0
        for case in blocking_cases:
            has_intent, segments = has_multi_player_keywords_enhanced(case)
            if has_intent:
                print(f"✅ GOOD: '{case}' was correctly blocked")
                blocking_passed += 1
            else:
                print(f"❌ BAD: '{case}' was NOT blocked when it should be")
        
        print(f"\nBlocking test: {blocking_passed}/{len(blocking_cases)} passed")
        
        overall_success = (permissive_passed == len(permissive_cases) and 
                          blocking_passed == len(blocking_cases))
        
        return overall_success
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_permissive_validation():
    """Test that validation is more permissive"""
    print("\n" + "=" * 70)
    print("TESTING PERMISSIVE VALIDATION")
    print("=" * 70)
    
    try:
        from player_matching_validator import validate_player_matches
        
        # Test cases that should pass validation (permissive)
        test_cases = [
            {
                'text': "How is Okert looking tonight?",
                'players': [{'name': 'Steven Okert', 'team': 'Astros'}],
                'should_pass': True
            },
            {
                'text': "What about Judge for tonight?", 
                'players': [{'name': 'Aaron Judge', 'team': 'Yankees'}],
                'should_pass': True
            },
            {
                'text': "Soto stats looking good",
                'players': [{'name': 'Juan Soto', 'team': 'Padres'}],
                'should_pass': True
            },
            {
                'text': "should we bail on Okert or is it early enough",
                'players': [{'name': 'Steven Okert', 'team': 'Astros'}],
                'should_pass': True
            }
        ]
        
        passed = 0
        for i, case in enumerate(test_cases):
            validated = validate_player_matches(case['text'], case['players'])
            
            if case['should_pass']:
                if validated:
                    print(f"✅ CASE {i+1}: '{case['text']}' correctly validated {case['players'][0]['name']}")
                    passed += 1
                else:
                    print(f"❌ CASE {i+1}: '{case['text']}' incorrectly rejected {case['players'][0]['name']}")
            else:
                if not validated:
                    print(f"✅ CASE {i+1}: '{case['text']}' correctly rejected {case['players'][0]['name']}")
                    passed += 1
                else:
                    print(f"❌ CASE {i+1}: '{case['text']}' incorrectly validated {case['players'][0]['name']}")
        
        print(f"\nValidation test: {passed}/{len(test_cases)} passed")
        return passed == len(test_cases)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_integration():
    """Test the full integration with loaded data"""
    print("\n" + "=" * 70)
    print("TESTING FULL INTEGRATION")
    print("=" * 70)
    
    try:
        # Load players data
        from config import players_data
        from utils import load_players_from_json
        
        if not players_data:
            print("Loading players data...")
            loaded_players = load_players_from_json("players.json")
            players_data.clear()
            players_data.extend(loaded_players)
            print(f"Loaded {len(players_data)} players")
        
        from player_matching import check_player_mentioned
        
        # Test cases that should work with the permissive system
        test_cases = [
            {
                'query': "How is Okert looking tonight?",
                'expected': 'single_player',  # Should find Steven Okert
                'description': 'Simple single player question'
            },
            {
                'query': "should we bail on Okert or is it early enough that he can make up for tonight?",
                'expected': 'single_player',  # Should find Steven Okert, not be blocked
                'description': 'Complex single player question with "or"'
            },
            {
                'query': "Soto vs Judge who is better",
                'expected': 'blocked',  # Should be blocked as obvious comparison
                'description': 'Obvious multi-player comparison'
            }
        ]
        
        passed = 0
        for i, case in enumerate(test_cases):
            print(f"\nTEST {i+1}: {case['description']}")
            print(f"Query: '{case['query']}'")
            
            result = check_player_mentioned(case['query'])
            
            if case['expected'] == 'blocked':
                if result == "BLOCKED":
                    print(f"✅ CORRECT: Query was blocked as expected")
                    passed += 1
                else:
                    print(f"❌ INCORRECT: Query should have been blocked but got: {result}")
            elif case['expected'] == 'single_player':
                if result and result != "BLOCKED":
                    if isinstance(result, list):
                        print(f"✅ CORRECT: Found {len(result)} players: {[p['name'] for p in result]}")
                    else:
                        print(f"✅ CORRECT: Found player: {result['name']}")
                    passed += 1
                else:
                    print(f"❌ INCORRECT: Expected to find player but got: {result}")
            else:
                print(f"❓ UNKNOWN: Unexpected result: {result}")
        
        print(f"\nIntegration test: {passed}/{len(test_cases)} passed")
        return passed == len(test_cases)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all permissive system tests"""
    print("🔧 PERMISSIVE SYSTEM TEST")
    print("Testing the simplified, permissive multi-player detection system")
    print()
    
    test1_passed = test_permissive_multi_player_detection()
    test2_passed = test_permissive_validation()
    test3_passed = test_full_integration()
    
    print("\n" + "=" * 70)
    print("PERMISSIVE SYSTEM TEST RESULTS")
    print("=" * 70)
    
    if test1_passed and test2_passed and test3_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Multi-player detection is more permissive")
        print("✅ Validation is more permissive")
        print("✅ Full integration works correctly")
        print("\n🚀 The system now defaults to being permissive rather than restrictive!")
        return True
    else:
        print("❌ SOME TESTS FAILED!")
        if not test1_passed:
            print("❌ Multi-player detection issue")
        if not test2_passed:
            print("❌ Validation issue")
        if not test3_passed:
            print("❌ Integration issue")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
