#!/usr/bin/env python3

"""
Final verification test to ensure both issues are resolved:
1. log_memory_usage function is available
2. Common English words are not validated as player names
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_log_memory_usage():
    """Test that log_memory_usage function is available and working"""
    print("=" * 60)
    print("TESTING log_memory_usage FUNCTION")
    print("=" * 60)
    
    try:
        from logging_system import log_memory_usage
        print("✅ log_memory_usage imported successfully")
        
        # Test the function
        log_memory_usage("Test Stage", "test_request_123")
        print("✅ log_memory_usage function executed successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Function error: {e}")
        return False

def test_validation_fix():
    """Test that common English words are rejected as player names"""
    print("\n" + "=" * 60)
    print("TESTING VALIDATION FIX")
    print("=" * 60)
    
    try:
        from player_matching_validator import validate_player_matches
        
        question = "should we bail on Okert or is it early enough that he can make up for tonight?"
        
        # Test that common words are rejected
        common_words = ['should', 'bail', 'early', 'enough', 'that', 'make']
        all_rejected = True
        
        for word in common_words:
            mock_players = [{'name': word, 'team': 'Unknown'}]
            validated = validate_player_matches(question, mock_players)
            
            if validated:
                print(f"❌ FAILED: '{word}' was incorrectly validated as a player name")
                all_rejected = False
            else:
                print(f"✅ PASSED: '{word}' was correctly rejected")
        
        # Test that real player names still work
        real_player = [{'name': 'okert', 'team': 'Giants'}]
        validated = validate_player_matches(question, real_player)
        
        if validated:
            print(f"✅ PASSED: Real player 'okert' was correctly validated")
        else:
            print(f"❌ FAILED: Real player 'okert' was incorrectly rejected")
            all_rejected = False
        
        return all_rejected
        
    except Exception as e:
        print(f"❌ Validation test error: {e}")
        return False

def test_bot_import():
    """Test that bot.py imports without errors"""
    print("\n" + "=" * 60)
    print("TESTING BOT.PY IMPORT")
    print("=" * 60)
    
    try:
        import bot
        print("✅ bot.py imported successfully")
        return True
    except Exception as e:
        print(f"❌ Bot import error: {e}")
        return False

def main():
    """Run all tests"""
    print("🔧 FINAL VERIFICATION TEST")
    print("Testing fixes for:")
    print("1. Undefined log_memory_usage function")
    print("2. Common English words being validated as player names")
    print()
    
    test1_passed = test_log_memory_usage()
    test2_passed = test_validation_fix()
    test3_passed = test_bot_import()
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    
    if test1_passed and test2_passed and test3_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ log_memory_usage function is working")
        print("✅ Validation fix is working")
        print("✅ Bot imports successfully")
        print("\n🚀 Both critical issues have been resolved!")
        return True
    else:
        print("❌ SOME TESTS FAILED!")
        if not test1_passed:
            print("❌ log_memory_usage function issue")
        if not test2_passed:
            print("❌ Validation fix issue")
        if not test3_passed:
            print("❌ Bot import issue")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
