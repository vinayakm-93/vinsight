from backend.services.finance import get_stock_history
import json

def test_history():
    ticker = "AAPL"
    ranges = [
        ("1d", "5m"),
        ("5d", "15m"),
        ("1mo", "60m"),
        ("1y", "1d")
    ]
    
    print(f"Testing history for {ticker}...")
    for period, interval in ranges:
        print(f"\n--- Testing Period: {period}, Interval: {interval} ---")
        try:
            data = get_stock_history(ticker, period, interval)
            print(f"Count: {len(data)}")
            if len(data) > 0:
                print(f"First Record: {data[0]}")
                print(f"Last Record: {data[-1]}")
            else:
                print("WARNING: No data returned")
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    test_history()
