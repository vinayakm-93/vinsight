
import sys
import os
import logging

# Setup Path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.services.yahoo_client import get_chart_data, get_quote_summary

logging.basicConfig(level=logging.INFO)

print("--- Testing Yahoo Client Connectivity ---")
ticker = "NVDA"

print(f"Fetching chart for {ticker}...")
chart = get_chart_data(ticker, interval="1d", range_="1mo")

if chart:
    print(f"Chart Success! Rows: {len(chart.get('timestamp', []))}")
else:
    print("Chart Failed.")

print(f"Fetching quote for {ticker}...")
quote = get_quote_summary(ticker)

if quote:
    print("Quote Success!")
    # print keys
    # print(quote.keys())
else:
    print("Quote Failed.")
