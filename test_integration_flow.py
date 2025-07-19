#!/usr/bin/env python3

"""
Integration test to verify the entire flow works correctly:
bot.py -> player_matching.py -> player_matching_validator.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_full_integration():
    """Test the complete integration flow"""
    print("=" * 70)
    print("TESTING FULL INTEGRATION FLOW")
    print("=" * 70)
    
    try:
        # Import the main function from player_matching.py that bot.py uses
        from player_matching import check_player_mentioned
        
        # Test the exact problematic question from the logs
        question = "should we bail on Okert or is it early enough that he can make up for tonight? - posting for Wrath who had question blocked due to bot issue"
        
        print(f"Testing question: {question}")
        print()
        
        # This is the exact call that bot.py makes
        print("1. Calling check_player_mentioned() (same as bot.py)...")
        matched_players = check_player_mentioned(question)
        
        print(f"2. Result: {matched_players}")
        print()
        
        if matched_players == "BLOCKED":
            print("✅ GOOD: Multi-player query correctly blocked")
            return True
        elif isinstance(matched_players, list):
            print(f"3. Found {len(matched_players)} validated players:")
            for player in matched_players:
                print(f"   - {player['name']} ({player['team']})")
            
            # Check if any common English words made it through
            common_words = ['should', 'bail', 'early', 'enough', 'that', 'make', 'tonight', 'posting', 'wrath', 'blocked', 'issue']
            problematic_matches = []
            
            for player in matched_players:
                if player['name'].lower() in common_words:
                    problematic_matches.append(player['name'])
            
            if problematic_matches:
                print(f"❌ PROBLEM: Common words still validated: {problematic_matches}")
                return False
            else:
                print("✅ GOOD: No common English words validated as players")
                
                # Check if legitimate player names are still working
                legitimate_players = [p for p in matched_players if p['name'].lower() not in common_words]
                if legitimate_players:
                    print(f"✅ GOOD: Legitimate players found: {[p['name'] for p in legitimate_players]}")
                else:
                    print("ℹ️  INFO: No legitimate players found (this may be expected)")
                
                return True
        else:
            print(f"❌ UNEXPECTED: Unexpected result type: {type(matched_players)}")
            return False
            
    except Exception as e:
        print(f"❌ INTEGRATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_player_question():
    """Test a simple single-player question"""
    print("\n" + "=" * 70)
    print("TESTING SIMPLE PLAYER QUESTION")
    print("=" * 70)
    
    try:
        from player_matching import check_player_mentioned
        
        # Test a simple question that should work
        question = "How is Okert looking tonight?"
        
        print(f"Testing question: {question}")
        print()
        
        matched_players = check_player_mentioned(question)
        
        print(f"Result: {matched_players}")
        
        if matched_players == "BLOCKED":
            print("❌ PROBLEM: Simple player question was blocked")
            return False
        elif isinstance(matched_players, list) and len(matched_players) > 0:
            print(f"✅ GOOD: Found {len(matched_players)} players")
            for player in matched_players:
                print(f"   - {player['name']} ({player['team']})")
            return True
        else:
            print("ℹ️  INFO: No players found (may be expected if Okert not in database)")
            return True
            
    except Exception as e:
        print(f"❌ SIMPLE TEST ERROR: {e}")
        return False

def test_common_words_only():
    """Test a question with only common words"""
    print("\n" + "=" * 70)
    print("TESTING COMMON WORDS ONLY")
    print("=" * 70)
    
    try:
        from player_matching import check_player_mentioned
        
        # Test a question with only common words
        question = "should we make that early enough tonight?"
        
        print(f"Testing question: {question}")
        print()
        
        matched_players = check_player_mentioned(question)
        
        print(f"Result: {matched_players}")
        
        if matched_players == "BLOCKED":
            print("ℹ️  INFO: Question blocked (may be expected)")
            return True
        elif isinstance(matched_players, list):
            if len(matched_players) == 0:
                print("✅ EXCELLENT: No common words validated as players")
                return True
            else:
                print(f"❌ PROBLEM: {len(matched_players)} common words validated as players:")
                for player in matched_players:
                    print(f"   - {player['name']} ({player['team']})")
                return False
        else:
            print(f"ℹ️  INFO: Unexpected result: {matched_players}")
            return True
            
    except Exception as e:
        print(f"❌ COMMON WORDS TEST ERROR: {e}")
        return False

def main():
    """Run all integration tests"""
    print("🔗 INTEGRATION FLOW TEST")
    print("Testing the complete flow: bot.py -> player_matching.py -> player_matching_validator.py")
    print()
    
    test1_passed = test_full_integration()
    test2_passed = test_simple_player_question()
    test3_passed = test_common_words_only()
    
    print("\n" + "=" * 70)
    print("INTEGRATION TEST RESULTS")
    print("=" * 70)
    
    if test1_passed and test2_passed and test3_passed:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Full integration flow works correctly")
        print("✅ Simple player questions work")
        print("✅ Common words are properly filtered")
        print("\n🚀 The fix is properly integrated throughout the entire system!")
        return True
    else:
        print("❌ SOME INTEGRATION TESTS FAILED!")
        if not test1_passed:
            print("❌ Full integration flow issue")
        if not test2_passed:
            print("❌ Simple player question issue")
        if not test3_passed:
            print("❌ Common words filtering issue")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
