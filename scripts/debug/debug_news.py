import yfinance as yf
import json

def test_news():
    ticker = "AAPL"
    print(f"Fetching news for {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        print(json.dumps(news, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_news()
