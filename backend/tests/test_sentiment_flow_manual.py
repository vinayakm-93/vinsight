import sys
import os
from datetime import datetime

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.finnhub_news import fetch_company_news
from services.analysis import analyze_sentiment_ondemand
from services.cache import clear_cache
from services.groq_sentiment import GroqSentimentAnalyzer

def test_flow():
    ticker = "AAPL"
    print(f"--- Testing Sentiment Flow for {ticker} ---")
    
    # 1. Clear Cache
    print("1. Clearing Cache...")
    clear_cache()
    
    # 2. Fetch News (Direct Link)
    print("2. Testing Finnhub Fetch...")
    news = fetch_company_news(ticker, days=7)
    print(f"   Latest News Count: {len(news.get('latest', []))}")
    print(f"   History News Count: {len(news.get('historical', []))}")
    
    if not news['latest'] and not news['historical']:
        print("   WARNING: No news returned. Verify API Key permission.")
        
    # 3. Test Full Analysis (includes Groq + Quant)
    print("3. Testing Full Analysis (Groq + Quant)...")
    result = analyze_sentiment_ondemand(ticker)
    
    print("\n--- RESULT ---")
    print(f"Scores -> Today: {result['score_today']}, Weekly: {result['score_weekly']}, Quant: {result['score_quant']}")
    print(f"Reasoning: {result['reasoning'][:100]}...")
    print(f"Article Count: {result['article_count']}")
    print(f"Source: {result['source']}")
    
    if result.get('source') == 'finnhub_v2':
        print("\nSUCCESS: Pipeline operational.")
    else:
        print(f"\nFAILURE: Unexpected source {result.get('source')}")

if __name__ == "__main__":
    try:
        test_flow()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
