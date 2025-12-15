import yfinance as yf
import json

def test_info():
    ticker = "AAPL"
    print(f"Fetching info for {ticker}...")
    stock = yf.Ticker(ticker)
    info = stock.info
    
    # Filter for relevant keys to avoid huge output
    keys_of_interest = ['regularMarketChange', 'regularMarketChangePercent', 'regularMarketPrice', 'regularMarketTime', 'symbol', 'shortName', 'previousClose']
    subset = {k: info.get(k) for k in keys_of_interest}
    
    print(json.dumps(subset, indent=2))

if __name__ == "__main__":
    test_info()
