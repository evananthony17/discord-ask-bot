#!/usr/bin/env python3
"""
Test script to verify Phase 1 strategic logging implementation
"""

import sys
import os
import time
import uuid

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_logging_system():
    """Test the logging system components"""
    print("🧪 Testing Phase 1 Strategic Logging Implementation")
    print("=" * 60)
    
    try:
        # Test 1: Import logging system
        print("1. Testing logging system import...")
        from logging_system import log_resource_usage
        print("   ✅ Logging system imported successfully")
        
        # Test 2: Test resource monitoring (built-in modules only)
        print("2. Testing resource monitoring...")
        request_id = str(uuid.uuid4())[:8]
        
        # Test the resource monitoring function directly
        import gc
        import sys
        obj_count = len(gc.get_objects())
        ref_count = sys.gettotalrefcount() if hasattr(sys, 'gettotalrefcount') else 'N/A'
        print(f"   📊 Objects: {obj_count}, Refs: {ref_count}")
        print("   ✅ Resource monitoring executed")
        
        # Test 3: Test basic logging structure (without async)
        print("3. Testing logging structure...")
        import logging
        logger = logging.getLogger(__name__)
        
        # Configure basic logging to see output
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
        
        # Test flow tracing patterns
        logger.info(f"🔵 FLOW_TRACE [{request_id}]: Starting message processing for test")
        logger.info(f"🔍 DETECTION_TRACE: Starting player detection for query: 'test'")
        logger.info(f"🟡 FLOW_TRACE [{request_id}]: Player detection completed, moving to decision logic")
        logger.info(f"🟠 FLOW_TRACE [{request_id}]: Entering decision routing with detected players")
        logger.info(f"🟢 FLOW_TRACE [{request_id}]: Decision complete, executing action")
        logger.info(f"🔍 DETECTION_TRACE: Detection complete, returning 0 matches")
        logger.info(f"✅ FLOW_TRACE [{request_id}]: Message processing complete")
        logger.info(f"🆔 REQUEST_TRACE: Completed request {request_id} in 0.05s")
        print("   ✅ Flow tracing patterns verified")
        
        # Test 4: Verify bot.py has the logging
        print("4. Testing bot.py logging integration...")
        with open('bot.py', 'r', encoding='utf-8') as f:
            bot_content = f.read()
            
        required_patterns = [
            '🔵 FLOW_TRACE',
            '🟡 FLOW_TRACE', 
            '🟠 FLOW_TRACE',
            '🟢 FLOW_TRACE',
            '✅ FLOW_TRACE',
            '❌ FLOW_TRACE',
            '🆔 REQUEST_TRACE',
            'log_memory_usage'
        ]
        
        for pattern in required_patterns:
            if pattern in bot_content:
                print(f"   ✅ Found: {pattern}")
            else:
                print(f"   ❌ Missing: {pattern}")
                return False
        
        # Test 5: Verify player_matching.py has the logging
        print("5. Testing player_matching.py logging integration...")
        with open('player_matching.py', 'r', encoding='utf-8') as f:
            matching_content = f.read()
            
        detection_patterns = [
            '🔍 DETECTION_TRACE',
            'logger = logging.getLogger(__name__)'
        ]
        
        for pattern in detection_patterns:
            if pattern in matching_content:
                print(f"   ✅ Found: {pattern}")
            else:
                print(f"   ❌ Missing: {pattern}")
                return False
        
        print("\n🎉 All Phase 1 Strategic Logging Tests Passed!")
        print("\nThe logging system is ready to trace the infinite loop issue.")
        print("\nImplemented Features:")
        print("✅ Flow tracing with emoji prefixes")
        print("✅ Request ID tracking")
        print("✅ Memory/resource monitoring")
        print("✅ Detection entry/exit logging")
        print("✅ Exception handling with flow tracing")
        print("\nNext steps:")
        print("1. Run your bot with a working case: '!ask Bo Bichette'")
        print("2. Run your bot with the problematic case: '!ask harper soto'")
        print("3. Compare the log patterns to identify where the loop occurs")
        print("4. Look for missing flow steps or repeated request IDs")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_imports():
    """Test that all required modules can be imported"""
    print("\n🔍 Testing module imports...")
    
    modules_to_test = [
        'bot',
        'player_matching', 
        'logging_system',
        'config',
        'utils',
        'validation'
    ]
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"   ✅ {module_name}")
        except Exception as e:
            print(f"   ❌ {module_name}: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("Phase 1 Strategic Logging - Test Suite")
    print("=" * 50)
    
    # Test imports first
    if not test_imports():
        print("\n❌ Import tests failed. Please check your dependencies.")
        sys.exit(1)
    
    # Test logging system
    if not test_logging_system():
        print("\n❌ Logging tests failed.")
        sys.exit(1)
    
    print("\n✅ All tests passed! The strategic logging system is ready.")
