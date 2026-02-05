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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip() # Optional: For reliable search
print(f"DEBUG: SERPER_API_KEY loaded: {'YES' if SERPER_API_KEY else 'NO (env var missing)'}")

# Configure Groq
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)
else:
    groq_client = None

# Configure Gemini
import google.generativeai as genai
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('models/gemini-2.0-flash', generation_config={"response_mime_type": "application/json"})
    except:
        gemini_model = None
else:
    gemini_model = None


def search_transcript_url(ticker: str, quarter: int = None, year: int = None):
    """
    Finds the Motley Fool transcript URL using Serper (if avail) or DuckDuckGo.
    Includes explicit timeouts, retries, and broadening queries.
    """
    # Try different query variations to increase success rate
    queries = []
    if not quarter or not year:
        queries.append(f"{ticker} earnings call transcript site:fool.com")
        queries.append(f"{ticker} earnings transcript Motley Fool")
    else:
        queries.append(f"{ticker} Q{quarter} {year} earnings call transcript site:fool.com")
        queries.append(f"{ticker} {ticker} Q{quarter} {year} transcript")

    # 1. Try Serper (Reliable)
    if SERPER_API_KEY:
        for q in queries[:1]: # Only use the best query with Serper to save credits
            for attempt in range(2):
                try:
                    url = "https://google.serper.dev/search"
                    payload = json.dumps({"q": q})
                    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
                    response = requests.post(url, headers=headers, data=payload, timeout=5)
                    results = response.json()
                    if 'organic' in results:
                        for item in results['organic']:
                            link = item.get('link', '')
                            if "fool.com" in link and "transcript" in link:
                                print(f"DEBUG: Found URL via Serper: {link}")
                                return link
                    break 
                except Exception as e:
                    print(f"DEBUG: Serper Search attempt {attempt+1} failed: {e}")

    # 2. Try DuckDuckGo (Modern DDGS pattern + Retries)
    from duckduckgo_search import DDGS
    for q in queries:
        print(f"DEBUG: Attempting DuckDuckGo Search: '{q}'")
        for attempt in range(2):
            try:
                with DDGS(timeout=5) as ddgs:
                    results = list(ddgs.text(q, max_results=5))
                    print(f"DEBUG: DDG found {len(results)} total results for '{q}' (attempt {attempt+1})")
                    for r in results:
                        link = r.get('href', '')
                        if "fool.com" in link and "transcript" in link:
                            print(f"DEBUG: SUCCESS: Found Fool.com URL via DDG: {link}")
                            return link
                break 
            except Exception as e:
                print(f"DEBUG: DDG Search attempt {attempt+1} for '{q}' failed: {e}")

    # 3. Try Generic Google Search (Fallback)
    try:
        from googlesearch import search
        for q in queries:
            print(f"DEBUG: Attempting Google Search Scraper for '{q}'...")
            try:
                # Using a strict timeout for the generator
                for url in search(q, num_results=5, timeout=5):
                    if "fool.com" in url and "transcript" in url:
                        print(f"DEBUG: SUCCESS: Found Fool.com URL via Google Scraping: {url}")
                        return url
            except:
                continue
    except Exception as e:
        print(f"DEBUG: Google Search failed: {e}")

    print(f"DEBUG: CRITICAL: All search attempts exhausted for {ticker}. Check internet or site changes.")
    return None

def extract_transcript_from_fool(url: str):
    """
    Scrapes the transcript text from a Motley Fool URL.
    """
    print(f"DEBUG: SCRAPER: Starting extraction from: {url}")
    try:
        ua = UserAgent()
        headers = {
            "User-Agent": ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        # Increase timeout and add retry for scraping
        for attempt in range(2):
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    print(f"DEBUG: SCRAPER: Successfully fetched page (200 OK)")
                    break
                print(f"DEBUG: SCRAPER Error: Status {resp.status_code} (attempt {attempt+1})")
            except Exception as e:
                 print(f"DEBUG: SCRAPER Exception for {url}: {e} (attempt {attempt+1})")
        
        if 'resp' not in locals() or resp.status_code != 200:
            print("DEBUG: SCRAPER: Giving up after 2 attempts.")
            return None
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Fool.com structure
        article_body = soup.find('div', class_='article-body')
        selector_used = "article-body"
        
        if not article_body:
             article_body = soup.find('div', class_='tailwind-article-body')
             selector_used = "tailwind-article-body"
        
        full_text = ""
        if article_body:
            print(f"DEBUG: SCRAPER: Extracting via primary selector '{selector_used}'")
            # Add newlines between paragraphs
            for p in article_body.find_all(['p', 'h2', 'h3']):
                full_text += p.get_text() + "\n\n"
        else:
            print("DEBUG: SCRAPER WARNING: Content div not found. Falling back to generic <p> tag scraping.")
            # Fallback
            paragraphs = soup.find_all('p')
            full_text = "\n".join([p.get_text() for p in paragraphs])
            
        cleaned_text = full_text.strip()
        print(f"DEBUG: SCRAPER SUCCESS: Extracted {len(cleaned_text)} characters of text.")
        return cleaned_text if len(cleaned_text) > 100 else None

    except Exception as e:
        print(f"DEBUG: SCRAPER CRITICAL ERROR: {e}")
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
    Fetches transcript (DIY Scrape) and analyzes with Groq -> Gemini Fallback.
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
             # Parse existing content to see if source data is there, else default
             try:
                 content_json = json.loads(latest_cache.content)
             except:
                 content_json = {}

             return {
                "summary": content_json,
                "metadata": {
                    "quarter": latest_cache.quarter,
                    "year": latest_cache.year,
                    "last_api_check": latest_cache.last_api_check.isoformat(),
                    "source": "Cache" # Ideally we stored source in DB, but cache is cache.
                }
            }

    # --- Fetch New Data ---
    if not groq_client and not gemini_model: 
        return {
            "error": "Missing AI API Keys (GROQ_API_KEY or GEMINI_API_KEY).",
            "error_code": "MISSING_AI_KEYS"
        }

    data_pkg = get_transcript_data(ticker)
    
    if not data_pkg:
        return {
            "error": "Could not locate transcript link on Motley Fool.",
            "error_code": "TRANSCRIPT_NOT_FOUND",
            "detail": "Search engines (Serper/DDG) failed to find the transcript URL."
        }

    transcript = data_pkg.get('transcript')
    if not transcript or len(transcript) < 500:
        return {
            "error": "Scraping failed or yielded insufficient content.",
            "error_code": "SCRAPE_FAILED",
            "detail": f"Transcript found at {data_pkg.get('url')} but content extraction failed."
        }

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
    
    data = None
    source_label = "Unknown"

    try:
        # ATTEMPT 1: GROQ
        if groq_client:
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
                source_label = "Llama 3.3 (Groq)"
                print(f"DEBUG: {source_label} Analysis Successful.")
            except Exception as e:
                print(f"DEBUG: Groq Earnings Analysis Failed/Rate-Limited: {e}. Falling back to Gemini 2.0...")
                if not gemini_model: raise e # No fallback available
        
        # ATTEMPT 2: GEMINI (Fallback or Primary if Groq missing)
        if not data and gemini_model:
            try:
                # Gemini 1.5 Flash
                response = gemini_model.generate_content(
                    f"You are a CFA. Output JSON only.\n{prompt}",
                    generation_config={"temperature": 0.2, "response_mime_type": "application/json"}
                )
                text = response.text
                data = json.loads(text)
                source_label = "Gemini 2.0 Flash (Fallback)" if groq_client else "Gemini 2.0 Flash"
                print(f"DEBUG: {source_label} Analysis Successful.")
            except Exception as e:
                print(f"DEBUG: Gemini Earnings Analysis Failed: {e}")
                return {
                    "error": "AI Strategy Analysis Failed",
                    "error_code": "AI_STRATEGY_FAILED",
                    "detail": f"Both Groq and Gemini providers failed: {str(e)}"
                }
        
        if not data:
             return {
                 "error": "AI Extraction Failed",
                 "error_code": "EMPTY_AI_RESPONSE",
                 "detail": "LLM returned no valid JSON content."
             }

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
                "source": f"{source_label} via Scraper"
            }
        }
        
    except Exception as e:
        return {"error": f"AI Processing Failed: {str(e)}"}
