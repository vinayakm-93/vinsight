import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import time

import yfinance as yf
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

def test_yfinance_links(ticker):
    print(f"--- Testing yfinance News for {ticker} ---")
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        
        found_url = None
        
        print(f"Found {len(news)} news items.")
        for item in news:
            title = item.get('title', '').lower()
            link = item.get('link', '')
            provider = item.get('publisher', '').lower()
            
            print(f"  - {title} ({provider})")
            
            # Check for Motley Fool Transcript
            if ("earnings" in title and "transcript" in title) or \
               ("fool.com" in link and "transcript" in link):
                print(f"    [MATCH] Found candidate: {link}")
                found_url = link
                break
        
        if not found_url:
            print("No transcript link found in recent news.")
            return

        print(f"Scraping {found_url}...")
        ua = UserAgent()
        headers = {"User-Agent": ua.random, "Accept": "text/html"}
        
        resp = requests.get(found_url, headers=headers, timeout=10)
        if resp.status_code == 200:
             print("Success! Page fetched.")
             if "Prepared Remarks" in resp.text:
                 print("Verified: Contains 'Prepared Remarks'.")
             else:
                 print("Warning: 'Prepared Remarks' not found, might be a different format.")
        else:
             print(f"Failed to fetch content: {resp.status_code}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_yfinance_links("AAPL")
    test_yfinance_links("NVDA")
