import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from services.finance import get_institutional_holders

def test_insider_window_filtering():
    print("Testing 90-day insider window filtering...")
    
    # Mock yfinance Ticker
    mock_ticker = MagicMock()
    
    # Create sample transactions
    now = datetime.now()
    data = {
        "Start Date": [
            now - timedelta(days=10),      # Recent (Discretionary)
            now - timedelta(days=45),      # Recent (Automatic)
            now - timedelta(days=85),      # Recent (Discretionary)
            now - timedelta(days=100),     # Old
            now - timedelta(days=150)      # Old
        ],
        "Insider": ["A", "B", "C", "D", "E"],
        "Position": ["Dir", "CEO", "CFO", "Dir", "Dir"],
        "Text": [
            "Sale at price", 
            "Stock award", 
            "Purchase at price", 
            "Sale at price", 
            "Sale at price"
        ],
        "Shares": [100, 200, 300, 400, 500],
        "Value": [1000, 2000, 3000, 4000, 5000]
    }
    mock_ticker.insider_transactions = pd.DataFrame(data)
    mock_ticker.info = {"heldPercentInsiders": 0.1, "heldPercentInstitutions": 0.5}
    mock_ticker.institutional_holders = pd.DataFrame()

    with patch('yfinance.Ticker', return_value=mock_ticker):
        result = get_institutional_holders("MOCK")
        
        txs = result.get("insider_transactions", [])
        print(f"Total transactions returned: {len(txs)}")
        
        # Verify count (should be 3)
        assert len(txs) == 3, f"Expected 3 transactions, got {len(txs)}"
        
        # Verify metadata
        meta = result.get("insider_metadata", {})
        assert meta.get("days_analyzed") == 90, f"Expected 90 days analyzed, got {meta.get('days_analyzed')}"
        assert meta.get("discretionary") == 2, f"Expected 2 discretionary, got {meta.get('discretionary')}"
        assert meta.get("automatic_10b5_1") == 1, f"Expected 1 automatic, got {meta.get('automatic_10b5_1')}"

    print("SUCCESS: Insider window filtering verified.")

if __name__ == "__main__":
    try:
        test_insider_window_filtering()
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)
