
import sys
import os
from unittest.mock import MagicMock
from fastapi import Request

# Mock constants for testing
os.environ["FINNHUB_API_KEY"] = "mock_key"
os.environ["GEMINI_API_KEY"] = "mock_key"

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from routes.watchlist import get_watchlist_summary
from sqlalchemy.orm import Session
import asyncio

def test_summary():
    # Mock DB
    db = MagicMock(spec=Session)
    
    # Mock Request
    request = MagicMock(spec=Request)
    request.headers = {"X-Guest-UUID": "test-uuid"}
    
    # Mock User
    user = None
    
    print("Testing get_watchlist_summary for ID -1...")
    try:
        result = get_watchlist_summary(
            watchlist_id=-1,
            refresh=True,
            symbols="AAPL,NVDA,MSFT,TSLA",
            db=db,
            user=user,
            request=request
        )
        print("Success!")
        print(result)
    except Exception as e:
        import traceback
        print("Caught Exception:")
        traceback.print_exc()

if __name__ == "__main__":
    test_summary()
