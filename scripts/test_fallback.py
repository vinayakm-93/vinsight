import sys
import os
from unittest.mock import MagicMock, patch

# Add backend to path so we can import services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

def test_yfinance_fallback():
    print("--- Starting Resilience Test: yfinance Fallback ---")
    
    # 1. Mock yfinance to simulate a 401/Blocked response (Empty data)
    mock_ticker = MagicMock()
    mock_ticker.info = {} # Empty info simulates block
    mock_ticker.history.return_value = MagicMock(empty=True) # Empty history simulates block
    
    # 2. Mock yahoo_client to ensure it's called
    with patch('yfinance.Ticker', return_value=mock_ticker):
        with patch('services.yahoo_client.get_quote_summary') as mock_qs:
            with patch('services.yahoo_client.get_chart_data') as mock_chart:
                
                # Setup mock responses for yahoo_client
                mock_qs.return_value = {
                    'price': {'regularMarketPrice': {'raw': 150.0}},
                    'summaryDetail': {'heldPercentInstitutions': {'raw': 0.75}}
                }
                mock_chart.return_value = {
                    'timestamp': [1700000000],
                    'indicators': {'quote': [{'close': [149.0], 'open': [148.0], 'high': [151.0], 'low': [147.0], 'volume': [1000000]}]}
                }
                
                from services.finance import fetch_coordinated_analysis_data
                
                print("Triggering fetch_coordinated_analysis_data('AAPL')...")
                result = fetch_coordinated_analysis_data("AAPL")
                
                # 3. Assertions
                assert result['info']['currentPrice'] == 150.0, f"Expected 150.0, got {result['info'].get('currentPrice')}"
                assert len(result['history']) > 0, "History should not be empty"
                assert result['history'][0]['Close'] == 149.0, f"Expected 149.0, got {result['history'][0].get('Close')}"
                
                print("SUCCESS: Fallback to yahoo_client verified.")
                print(f"Info currentPrice: {result['info']['currentPrice']}")
                print(f"History sample: {result['history'][0]}")

if __name__ == "__main__":
    try:
        test_yfinance_fallback()
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)
