import yfinance as yf
import json

def check_institutional_data(ticker):
    stock = yf.Ticker(ticker)
    print(f"--- Checking {ticker} ---")
    
    try:
        # Major Holders
        print("\n[Major Holders]")
        print(stock.major_holders)
    except Exception as e:
        print(f"Error getting major_holders: {e}")

    try:
        # Institutional Holders
        print("\n[Institutional Holders]")
        inst = stock.institutional_holders
        if inst is not None and not inst.empty:
            print(inst.head())
        else:
            print("No institutional holders data found.")
    except Exception as e:
        print(f"Error getting institutional_holders: {e}")
        
    try:
        # Mutual Fund Holders
        print("\n[Mutual Fund Holders]")
        mf = stock.mutualfund_holders
        if mf is not None and not mf.empty:
            print(mf.head())
    except Exception as e:
        print(f"Error getting mutualfund_holders: {e}")

if __name__ == "__main__":
    check_institutional_data("AAPL")
