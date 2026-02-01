
import os
import sys
import statistics
# Add backend to path to import services
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.finnhub_news import fetch_company_news
from dotenv import load_dotenv

load_dotenv()

def analyze_summaries():
    tickers = ['AAPL', 'TSLA', 'GOOGL', 'NVDA']
    all_lengths = []
    
    print(f"{'Ticker':<8} | {'Count':<5} | {'Min':<5} | {'Avg':<5} | {'Max':<5}")
    print("-" * 45)
    
    for ticker in tickers:
        news = fetch_company_news(ticker, days=7)
        # Combine latest and historical
        items = news.get('latest', []) + news.get('historical', [])
        
        lengths = [len(item.get('summary', '')) for item in items if item.get('summary')]
        
        if lengths:
            all_lengths.extend(lengths)
            avg_len = int(statistics.mean(lengths))
            print(f"{ticker:<8} | {len(lengths):<5} | {min(lengths):<5} | {avg_len:<5} | {max(lengths):<5}")
        else:
             print(f"{ticker:<8} | 0     | N/A   | N/A   | N/A")

    if all_lengths:
        print("\nOverall Stats:")
        print(f"Total Articles Analyzed: {len(all_lengths)}")
        print(f"Average Length: {int(statistics.mean(all_lengths))} chars")
        print(f"Median Length: {int(statistics.median(all_lengths))} chars")
        print(f"Min Length: {min(all_lengths)} chars")
        print(f"Max Length: {max(all_lengths)} chars")
        
        # Distribution
        under_100 = len([l for l in all_lengths if l < 100])
        between_100_400 = len([l for l in all_lengths if 100 <= l <= 400])
        over_400 = len([l for l in all_lengths if l > 400])
        
        print("\nDistribution:")
        print(f"< 100 chars:   {under_100} ({under_100/len(all_lengths)*100:.1f}%)")
        print(f"100-400 chars: {between_100_400} ({between_100_400/len(all_lengths)*100:.1f}%)")
        print(f"> 400 chars:   {over_400} ({over_400/len(all_lengths)*100:.1f}%)")

if __name__ == "__main__":
    if not os.getenv("FINNHUB_API_KEY"):
        print("Error: FINNHUB_API_KEY not found")
    else:
        analyze_summaries()
