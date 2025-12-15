
import yfinance as yf
import json

def check_holders(ticker):
    stock = yf.Ticker(ticker)
    print(f"--- {ticker} Major Holders ---")
    try:
        print(stock.major_holders)
    except Exception as e:
        print(e)
    
    print(f"\n--- {ticker} Institutional Holders ---")
    try:
        print(stock.institutional_holders)
    except Exception as e:
        print(e)
        
    print(f"\n--- {ticker} Insider Transactions ---")
    try:
        # Sometimes this gives info on owners/promoters selling/buying
        print(stock.insider_transactions.head())
    except Exception as e:
        print(e)

    print(f"\n--- {ticker} Info (ownership keys) ---")
    try:
        info = stock.info
        keys = [k for k in info.keys() if 'held' in k.lower() or 'insider' in k.lower() or 'institution' in k.lower()]
        for k in keys:
            print(f"{k}: {info[k]}")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    check_holders("AAPL")
