
import yfinance as yf
try:
    ticker = yf.Ticker("AAPL")
    print("Is fast_info available?", hasattr(ticker, "fast_info"))


    if hasattr(ticker, "fast_info"):
        fi = ticker.fast_info
        print(f"FastInfo yearChange: {fi.get('yearChange')}")
        
        # Calculate actual YTD from history
        import datetime
        current_year = datetime.datetime.now().year
        start_date = f"{current_year}-01-01"
        try:
            hist = ticker.history(start=start_date)
            if not hist.empty:
                start_price = hist['Close'].iloc[0]
                curr_price = fi.get('last_price') or hist['Close'].iloc[-1]
                ytd_manual = (curr_price - start_price) / start_price
                print(f"Manual YTD Calculation: {ytd_manual}")
                print(f"Difference: {abs(ytd_manual - fi.get('yearChange', -999))}")
            else:
                print("No history found for YTD")
        except Exception as e:
            print(f"History fetch error: {e}")


except Exception as e:
    print(f"Error: {e}")
