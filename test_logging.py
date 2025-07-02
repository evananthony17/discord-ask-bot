#!/usr/bin/env python3
"""
Test script to verify logging system is working
"""

import sys
import os

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logging_system import log_info, log_error, log_success, log_warning, log_debug

def test_logging():
    """Test all logging functions"""
    print("🧪 Testing logging system...")
    
    log_info("Testing INFO logging - this should appear in console")
    log_success("Testing SUCCESS logging - this should appear in console")
    log_warning("Testing WARNING logging - this should appear in console")
    log_error("Testing ERROR logging - this should appear in console")
    log_debug("Testing DEBUG logging - this should appear in console")
    
    print("🧪 Logging test complete. You should see 5 log messages above.")

if __name__ == "__main__":
    test_logging()
