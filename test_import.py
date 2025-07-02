# Simple test to verify imports work correctly
try:
    from logging_system import log_memory_usage
    print("✅ log_memory_usage imported successfully")
    
    # Test that the function exists and is callable
    if callable(log_memory_usage):
        print("✅ log_memory_usage is callable")
    else:
        print("❌ log_memory_usage is not callable")
        
    # Check the function signature
    import inspect
    sig = inspect.signature(log_memory_usage)
    print(f"✅ Function signature: {sig}")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Other error: {e}")

print("Import test completed")
