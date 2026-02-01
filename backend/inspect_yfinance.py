import yfinance as yf
import json
import logging

def inspect_yfinance_keys(ticker_symbol):
    print(f"Fetching info for {ticker_symbol}...")
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        # Print all keys sorted
        keys = sorted(info.keys())
        print(f"\nTotal Keys: {len(keys)}")
        print("-" * 30)
        for k in keys:
            val = info[k]
            # Truncate long values
            str_val = str(val)
            if len(str_val) > 50:
                str_val = str_val[:47] + "..."
            print(f"{k}: {str_val}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_yfinance_keys("AAPL")
