import os
import asyncio
from unittest.mock import patch
import sys

# Ensure backend limits 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
try:
    with open(env_path, 'r') as f:
        for line in f:
            if line.startswith('OPENROUTER_API_KEY='):
                os.environ['OPENROUTER_API_KEY'] = line.strip().split('=', 1)[1].strip("\"'")
            elif line.startswith('GEMINI_API_KEY='):
                os.environ['GEMINI_API_KEY'] = line.strip().split('=', 1)[1].strip("\"'")
except Exception as e:
    pass

from jobs.guardian_job import run_guardian_scan
from services.guardian import detect_events as original_detect_events

# Mock detect_events to always return a trigger for testing
def mock_detect_events(symbol, last_known_price=None):
    print(f"\\n> [MOCK] Forcing a trigger event for {symbol}...")
    return {
        "triggered": True,
        "events": [f"Mock Event: Price dropped abruptly by 15% due to simulated news anomaly for {symbol}."],
        "current_price": 100.0
    }

if __name__ == "__main__":
    print("--- Phase 4 Deep Integration Test ---")
    print("We are bypassing the 'Fast Filter' to simulate a breaking event, forcing the Guardian Job to summon the AI Agent and write an Alert to the Postgres DB.")
    with patch('services.guardian.detect_events', side_effect=mock_detect_events):
        asyncio.run(run_guardian_scan())
