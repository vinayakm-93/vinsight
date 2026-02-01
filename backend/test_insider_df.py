import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

stock = yf.Ticker("TSLA")
df = stock.insider_transactions
if df is not None and not df.empty:
    print(f"Columns: {df.columns.tolist()}")
    print(f"First row: {df.iloc[0].to_dict()}")
    
    # Try filtering
    if 'Start Date' in df.columns:
        df['Start Date'] = pd.to_datetime(df['Start Date'])
        cutoff = datetime.now() - timedelta(days=90)
        filtered = df[df['Start Date'] >= cutoff]
        print(f"Total: {len(df)}, Last 90 days: {len(filtered)}")
else:
    print("No data or empty")
