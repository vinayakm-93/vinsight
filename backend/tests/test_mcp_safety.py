
import unittest
import os
import time
import sys
import json
import shutil

# Add backend root to path to import mcp_server
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server import guard, GLOBAL_DAILY_LIMIT, HOURLY_LIMITS, LIMITS_FILE
# Mock imports
from unittest.mock import MagicMock
sys.modules['services.finnhub_news'] = MagicMock()
sys.modules['services.groq_sentiment'] = MagicMock()
sys.modules['services.earnings'] = MagicMock()
sys.modules['database'] = MagicMock()

TEST_LIMITS_FILE = "logs/mcp_limits.json"

class TestMCPSafety(unittest.TestCase):
    def setUp(self):
        # Clean state
        if os.path.exists("mcp_kill_switch.lock"):
            os.remove("mcp_kill_switch.lock")
        
        # Reset Guard State for Test
        # We manipulate the internal state to avoid waiting hours
        guard.usage_data = {"daily": {"count": 0, "reset_at": time.time() + 86400}, "hourly": {}}
        if os.path.exists(TEST_LIMITS_FILE):
            os.remove(TEST_LIMITS_FILE)

    def tearDown(self):
        if os.path.exists("mcp_kill_switch.lock"):
            os.remove("mcp_kill_switch.lock")

    def test_daily_limit(self):
        """Test Global Daily Limit."""
        print("\n--- Testing Global Daily Limit ---")
        
        # Artificial Fill
        guard.usage_data["daily"]["count"] = GLOBAL_DAILY_LIMIT
        
        # Attempt Call
        try:
             guard.check_limits("analyze_sentiment")
             self.fail("Should have raised RuntimeError")
        except RuntimeError as e:
             print(f"Blocked correctly: {e}")
             self.assertIn("DAILY_LIMIT_EXCEEDED", str(e))

    def test_hourly_limit(self):
        """Test Hourly Tool Limit."""
        print("\n--- Testing Hourly Limit ---")
        
        # Analyze Sentiment limit is 60/hr
        # Fill it up
        now = time.time()
        guard.usage_data["hourly"]["analyze_sentiment"] = [now] * 61
        
        try:
             guard.check_limits("analyze_sentiment")
             self.fail("Should have raised RuntimeError")
        except RuntimeError as e:
             print(f"Blocked correctly: {e}")
             self.assertIn("HOURLY_LIMIT_EXCEEDED", str(e))

    def test_persistence(self):
        """Test that usage persists to disk."""
        print("\n--- Testing Persistence ---")
        
        # Reset
        guard.usage_data = {"daily": {"count": 0, "reset_at": time.time() + 86400}, "hourly": {"test_tool": []}}
        
        # Make a call (simulated)
        guard.usage_data["daily"]["count"] += 1
        guard.usage_data["hourly"]["test_tool"].append(time.time())
        guard._save_usage()
        
        # Verify file exists
        self.assertTrue(os.path.exists(TEST_LIMITS_FILE))
        
        # Verify content
        with open(TEST_LIMITS_FILE, 'r') as f:
            data = json.load(f)
            self.assertEqual(data["daily"]["count"], 1)
            self.assertEqual(len(data["hourly"]["test_tool"]), 1)
            print("Persistence verified.")

if __name__ == '__main__':
    unittest.main()
