"""
Alpha Vantage News Sentiment API Integration
Provides news with built-in sentiment scores and article summaries.
"""

import os
import requests
from typing import Dict, List, Optional
from cachetools import TTLCache
import logging

logger = logging.getLogger(__name__)

# Cache for 15 minutes to avoid rate limiting (5 requests/min on free tier)
_news_cache = TTLCache(maxsize=100, ttl=900)


def get_alpha_vantage_news(ticker: str, limit: int = 10) -> Optional[Dict]:
    """
    Fetch news sentiment from Alpha Vantage API.
    
    Args:
        ticker: Stock ticker symbol
        limit: Max number of articles to return
        
    Returns:
        {
            'articles': [
                {
                    'title': str,
                    'summary': str,
                    'source': str,
                    'url': str,
                    'time_published': str,
                    'sentiment_score': float (-1 to 1),
                    'sentiment_label': str ('Bullish', 'Bearish', etc.),
                    'relevance_score': float (0 to 1)
                }
            ],
            'overall_sentiment': {
                'score': float,
                'label': str
            },
            'source': 'alpha_vantage'
        }
    """
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    
    if not api_key:
        logger.warning("ALPHA_VANTAGE_API_KEY not set, falling back to yfinance")
        return None
    
    # Check cache
    cache_key = f"av_news_{ticker}"
    if cache_key in _news_cache:
        logger.info(f"Returning cached Alpha Vantage news for {ticker}")
        return _news_cache[cache_key]
    
    try:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": ticker,
            "limit": limit,
            "apikey": api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Check for API errors
        if "Error Message" in data or "Note" in data:
            logger.error(f"Alpha Vantage API error: {data}")
            return None
        
        feed = data.get("feed", [])
        if not feed:
            logger.info(f"No news found for {ticker} on Alpha Vantage")
            return None
        
        articles = []
        total_sentiment = 0.0
        relevant_count = 0
        
        for item in feed[:limit]:
            # Get ticker-specific sentiment if available
            ticker_sentiment = None
            for ts in item.get("ticker_sentiment", []):
                if ts.get("ticker", "").upper() == ticker.upper():
                    ticker_sentiment = ts
                    break
            
            if ticker_sentiment:
                sentiment_score = float(ticker_sentiment.get("ticker_sentiment_score", 0))
                relevance = float(ticker_sentiment.get("relevance_score", 0))
            else:
                sentiment_score = float(item.get("overall_sentiment_score", 0))
                relevance = 0.5
            
            # Map Alpha Vantage labels to our standard labels
            av_label = item.get("overall_sentiment_label", "Neutral")
            if "Bullish" in av_label:
                label = "Positive"
            elif "Bearish" in av_label:
                label = "Negative"
            else:
                label = "Neutral"
            
            article = {
                "title": item.get("title", ""),
                "summary": item.get("summary", ""),
                "source": item.get("source", ""),
                "url": item.get("url", ""),
                "time_published": item.get("time_published", ""),
                "sentiment_score": sentiment_score,
                "sentiment_label": label,
                "relevance_score": relevance
            }
            articles.append(article)
            
            # Weight by relevance for overall score
            if relevance > 0.3:  # Only count relevant articles
                total_sentiment += sentiment_score * relevance
                relevant_count += relevance
        
        # Calculate weighted average sentiment
        if relevant_count > 0:
            avg_sentiment = total_sentiment / relevant_count
        else:
            avg_sentiment = 0.0
        
        # Determine overall label
        if avg_sentiment > 0.15:
            overall_label = "Positive"
        elif avg_sentiment < -0.15:
            overall_label = "Negative"
        else:
            overall_label = "Neutral"
        
        result = {
            "articles": articles,
            "overall_sentiment": {
                "score": avg_sentiment,
                "label": overall_label
            },
            "article_count": len(articles),
            "source": "alpha_vantage"
        }
        
        # Cache the result
        _news_cache[cache_key] = result
        
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching Alpha Vantage news: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None


def is_available() -> bool:
    """Check if Alpha Vantage API key is configured."""
    return os.getenv("ALPHA_VANTAGE_API_KEY") is not None


# Test function
if __name__ == "__main__":
    import json
    
    ticker = "AAPL"
    print(f"Testing Alpha Vantage news for {ticker}...")
    
    if not is_available():
        print("ERROR: ALPHA_VANTAGE_API_KEY not set")
        exit(1)
    
    result = get_alpha_vantage_news(ticker)
    
    if result:
        print(f"\nFound {result['article_count']} articles")
        print(f"Overall Sentiment: {result['overall_sentiment']['label']} ({result['overall_sentiment']['score']:.3f})")
        print("\nTop 3 articles:")
        for i, article in enumerate(result['articles'][:3]):
            print(f"\n{i+1}. {article['title'][:60]}...")
            print(f"   Sentiment: {article['sentiment_label']} ({article['sentiment_score']:.3f})")
            print(f"   Relevance: {article['relevance_score']:.2f}")
    else:
        print("No results returned")
