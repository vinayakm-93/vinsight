import os
import requests
import json
import re
from groq import Groq
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import EarningsAnalysis
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Env vars
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY") # Optional: For reliable search
print(f"DEBUG: SERPER_API_KEY loaded: {'YES' if SERPER_API_KEY else 'NO (env var missing)'}")

# Configure Groq
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)
else:
    groq_client = None

def search_transcript_url(ticker: str, quarter: int = None, year: int = None):
    """
    Finds the Motley Fool transcript URL using Serper (if avail) or DuckDuckGo.
    """
    if not quarter or not year:
        # Default to "latest" if not specified (though specific is better for caching)
        query = f"{ticker} earnings call transcript site:fool.com"
    else:
        query = f"{ticker} Q{quarter} {year} earnings call transcript site:fool.com"
    
    print(f"DEBUG: Searching for transcript: '{query}'")

    # 1. Try Serper (Reliable)
    if SERPER_API_KEY:
        try:
            url = "https://google.serper.dev/search"
            payload = json.dumps({"q": query})
            headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
            response = requests.post(url, headers=headers, data=payload)
            results = response.json()
            if 'organic' in results:
                for item in results['organic']:
                    link = item.get('link', '')
                    if "fool.com" in link and "transcript" in link:
                        return link
        except Exception as e:
            print(f"DEBUG: Serper Search failed: {e}")

    # 2. Try DuckDuckGo (Free, sometimes flaky)
    try:
        from duckduckgo_search import DDGS
        results = DDGS().text(query, max_results=5)
        for r in results:
            link = r.get('href', '')
            if "fool.com" in link and "transcript" in link:
                return link
    except Exception as e:
        print(f"DEBUG: DDG Search failed: {e}")

    # 3. Try Generic Google Search (Fallback)
    try:
        from googlesearch import search
        # search() yields URLs
        for url in search(query, num_results=5):
            if "fool.com" in url and "transcript" in url:
                return url
    except Exception as e:
        print(f"DEBUG: Google Search failed: {e}")

    return None

def extract_transcript_from_fool(url: str):
    """
    Scrapes the transcript text from a Motley Fool URL.
    """
    try:
        ua = UserAgent()
        headers = {
            "User-Agent": ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"DEBUG: Failed to fetch {url} - Status {resp.status_code}")
            return None
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Fool.com structure
        article_body = soup.find('div', class_='article-body')
        if not article_body:
             article_body = soup.find('div', class_='tailwind-article-body')
        
        full_text = ""
        if article_body:
            # Add newlines between paragraphs
            for p in article_body.find_all(['p', 'h2', 'h3']):
                full_text += p.get_text() + "\n\n"
        else:
            # Fallback
            paragraphs = soup.find_all('p')
            full_text = "\n".join([p.get_text() for p in paragraphs])
            
        return full_text.strip()

    except Exception as e:
        print(f"DEBUG: Scraping exception: {e}")
        return None

def get_transcript_data(ticker: str):
    """
    Orchestrates finding and scraping the transcript.
    Returns dict with text and metadata, or None.
    """
    # Infer 'latest' by not specifying Q/Y in search
    # Ideally, we'd parse the Date from the search result or page to know Q/Y.
    # For now, we search generic "earnings transcript" and assume the first result is latest.
    current_year = datetime.now().year
    
    url = search_transcript_url(ticker)
    if not url:
        return None
        
    print(f"DEBUG: Found Transcript URL: {url}")
    
    text = extract_transcript_from_fool(url)
    if not text:
        return None
        
    # Attempt to extract Quarter/Year from text logic or URL if possible
    # URL pattern: .../2024/01/25/...-q4-2023-...
    # Regex to find "Q[1-4] [0-9]{4}" in URL or Text
    
    quarter = "N/A"
    year = str(current_year)
    
    # Try match from URL first (more reliable)
    match = re.search(r'q([1-4])-(\d{4})', url) 
    if match:
        quarter = match.group(1)
        year = match.group(2)
    else:
        # Try match "fiscal year 2024" or "fourth quarter" in text
        pass

    return {
        "transcript": text,
        "quarter": quarter,
        "year": year,
        "url": url,
        "date": datetime.now().isoformat() # We don't have exact pub date easily
    }

def analyze_earnings(ticker: str, db: Session):
    """
    Fetches transcript (DIY Scrape) and analyzes with Groq.
    Implements Perpetual Caching (never expire old reports).
    """
    
    # 1. Check DB Cache for ANY recent report
    # Since we can't search by Q/Y before we scrape, we check the LATEST entry for this ticker.
    latest_cache = db.query(EarningsAnalysis).filter(EarningsAnalysis.ticker == ticker).order_by(EarningsAnalysis.id.desc()).first()
    
    # Check if cache is "fresh enough" to skip re-scraping the SAME quarter
    # If we have a report from < 3 months ago, it's likely the latest.
    if latest_cache:
        # Assuming earnings are every 3 months.
        # If the specific Q/Y is "N/A", we might want to re-scrape to fix it, but let's assume valid.
        days_since = (datetime.utcnow() - latest_cache.last_api_check).days
        if days_since < 60: # Conservative: if checked < 2 months ago, serve it.
             return {
                "summary": json.loads(latest_cache.content),
                "metadata": {
                    "quarter": latest_cache.quarter,
                    "year": latest_cache.year,
                    "last_api_check": latest_cache.last_api_check.isoformat(),
                    "source": "Cache"
                }
            }

    # --- Fetch New Data ---
    if not groq_client: 
        return {"error": "Missing GROQ_API_KEY."}

    data_pkg = get_transcript_data(ticker)
    
    if not data_pkg:
        return {"error": "Could not locate transcript. Try adding SERPER_API_KEY for reliable search."}

    transcript = data_pkg['transcript']
    q = data_pkg['quarter']
    y = data_pkg['year']
    
    # Check duplicate before Analyzing
    # If we scraped Q3 2024, and we already have Q3 2024 in DB, return DB version.
    existing = db.query(EarningsAnalysis).filter(
        EarningsAnalysis.ticker == ticker,
        EarningsAnalysis.quarter == q,
        EarningsAnalysis.year == y
    ).first()
    
    if existing:
         return {
            "summary": json.loads(existing.content),
            "metadata": {
                "quarter": existing.quarter,
                "year": existing.year,
                "last_api_check": existing.last_api_check.isoformat(),
                "source": "Cache (Matched Scrape)"
            }
        }

    # --- Run AI Analysis ---
    if len(transcript) > 50000:
        transcript = transcript[:50000] + "...(truncated)"
    
    prompt = f"""
    Role: Senior Wall Street Analyst (CFA).
    Task: Analyze this earnings transcript for {ticker} (Q{q} {y}).
    Target Audience: Retail Investor.

    CONTEXT:
    The text is scraped and may contain noise (ads, disclaimers). 
    IGNORE any text about "Premium services", "Stock Advisor", or navigation links.
    Focus ONLY on the CEO/Management remarks and the Q&A.

    INSTRUCTIONS:
    1. Infer "Prepared Remarks" vs "Q&A" even if headers are fuzzy.
    2. Be objective, slightly skeptical.
    3. JSON output ONLY.

    OUTPUT FORMAT:
    {{
      "prepared_remarks": {{
        "sentiment": "Bullish|Bearish|Neutral",
        "summary": "Strategic narrative summary.",
        "key_points": ["Point 1", "Point 2"]
      }},
      "qa_session": {{
        "sentiment": "Bullish|Bearish|Neutral",
        "summary": "Analyst Q&A tone and management confidence.",
        "revelations": ["Hidden risk", "Guidance clarity"]
      }},
      "verdict": {{
        "rating": "Buy|Hold|Sell",
        "reasoning": "Decisive conclusion."
      }}
    }}
    
    Transcript:
    {transcript}
    """
    
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a CFA. Output JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        text = completion.choices[0].message.content
        data = json.loads(text)
        
        # Save to DB (Perpetual)
        new_analysis = EarningsAnalysis(
            ticker=ticker,
            quarter=q,
            year=y,
            content=json.dumps(data),
            last_api_check=datetime.utcnow()
        )
        db.add(new_analysis)  
        db.commit()
            
        return {
            "summary": data,
            "metadata": {
                "quarter": q,
                "year": y,
                "last_api_check": datetime.utcnow().isoformat(),
                "source": f"Scraper ({data_pkg['url']})"
            }
        }
        
    except Exception as e:
        return {"error": f"AI Processing Failed: {str(e)}"}
