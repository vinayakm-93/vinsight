import os
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Constants
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"

def get_api_key() -> str:
    key = os.getenv("FINNHUB_API_KEY")
    if not key:
        print("Warning: FINNHUB_API_KEY not found in environment variables.")
        return ""
    return key

def fetch_company_news(ticker: str, days: int = 7) -> Dict[str, List[Dict]]:
    """
    Fetches company news from Finnhub for the last N days.
    Returns a dictionary separated into 'latest' (< 24h) and 'historical' (> 24h).
    """
    api_key = get_api_key()
    if not api_key:
        return {"latest": [], "historical": []}

    # Calculate dates (YYYY-MM-DD)
    now = datetime.now()
    start_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = now.strftime("%Y-%m-%d")
    
    # 24 Hour Cutoff Timestamp (Unix)
    cutoff_24h = int((now - timedelta(hours=24)).timestamp())

    url = f"{FINNHUB_BASE_URL}/company-news"
    params = {
        "symbol": ticker,
        "from": start_date,
        "to": end_date,
        "token": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 429:
            print(f"Finnhub Rate Limit Hit for {ticker}")
            return {"latest": [], "historical": []}
            
        if response.status_code != 200:
            print(f"Finnhub Error {response.status_code}: {response.text}")
            return {"latest": [], "historical": []}

        articles = response.json()
        
        latest_news = []
        historical_news = []
        
        # Sort by datetime desc (Finnhub usually returns desc, but ensure it)
        # Note: Finnhub 'datetime' is a unix timestamp e.g. 1569052651
        articles.sort(key=lambda x: x.get('datetime', 0), reverse=True)

        for article in articles:
            # Skip articles with no summary (useless for LLM)
            if not article.get('summary'):
                continue

            # Standardize structure
            news_item = {
                "title": article.get('headline'),
                "summary": article.get('summary'),
                "source": article.get('source'),
                "url": article.get('url'),
                "datetime": article.get('datetime'), # Unix timestamp
                "date_str": datetime.fromtimestamp(article.get('datetime', 0)).strftime("%Y-%m-%d %H:%M")
            }

            # Partition
            if article.get('datetime', 0) >= cutoff_24h:
                if len(latest_news) < 10: # Cap latest at 10
                    latest_news.append(news_item)
            else:
                if len(historical_news) < 40: # Increased cap for better 7-day coverage
                    historical_news.append(news_item)

        return {
            "latest": latest_news,
            "historical": historical_news
        }

    except Exception as e:
        print(f"Exception fetching Finnhub news for {ticker}: {e}")
        return {"latest": [], "historical": []}
