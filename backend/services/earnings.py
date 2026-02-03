import os
import requests
import json
from groq import Groq
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import EarningsAnalysis

# Env vars should be loaded by main app or environment
API_NINJAS_KEY = os.getenv("API_NINJAS_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Configure Groq if key exists
groq_client = None
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)

def get_transcript(ticker: str):
    """Fetches earnings transcript from API Ninjas."""
    if not API_NINJAS_KEY:
        print("DEBUG: Missing API_NINJAS_KEY environment variable.")
        return None

    api_url = f'https://api.api-ninjas.com/v1/earningstranscript?ticker={ticker}'
    
    try:
        response = requests.get(api_url, headers={'X-Api-Key': API_NINJAS_KEY})
        
        if response.status_code == 200:
            data = response.json()
            if not data:
                return None 
            
            if isinstance(data, list) and len(data) > 0:
                item = data[0]
                return {
                    "transcript": item.get('transcript'),
                    "quarter": str(item.get('quarter')),
                    "year": str(item.get('year')),
                    "date": item.get('date')
                }
            elif isinstance(data, dict):
                return {
                    "transcript": data.get('transcript'),
                    "quarter": str(data.get('quarter')),
                    "year": str(data.get('year')),
                    "date": data.get('date')
                }
            else:
                 return None
        else:
            return None
    except Exception as e:
        print(f"DEBUG: Exception fetching transcript: {e}")
        return None

def analyze_earnings(ticker: str, db: Session):
    """
    Fetches transcript and returns structured summary.
    Checks DB cache first.
    Refreshes cache IF:
    1. Cache doesn't exist.
    2. Cache exists but 'last_api_check' was > 24 hours ago (Staleness Check).
    """
    
    # 1. Check DB Cache (Get latest for ticker)
    # Ideally should get by specific quarter/year if known, but here we just want "latest available" 
    # effectively matching previous logic.
    # Actually, the API returns the "latest" transcript usually. 
    # So we should check if we already have the analysis for the "latest" transcript.
    # But we don't know what is "latest" until we ask the API, or we rely on our stored data.
    
    # Strategy:
    # 1. Check if we have ANY analysis for this ticker.
    # 2. If we do, check 'last_api_check'.
    # 3. If fresh (<24h), return it.
    
    cached_analysis = db.query(EarningsAnalysis).filter(EarningsAnalysis.ticker == ticker).order_by(EarningsAnalysis.year.desc(), EarningsAnalysis.quarter.desc()).first()
    
    should_check_api = True
    if cached_analysis:
        if datetime.utcnow() - cached_analysis.last_api_check < timedelta(hours=24):
            should_check_api = False
            
    if not should_check_api and cached_analysis:
        return {
            "summary": json.loads(cached_analysis.content),
            "metadata": {
                "quarter": cached_analysis.quarter,
                "year": cached_analysis.year,
                "last_api_check": cached_analysis.last_api_check.isoformat()
            }
        }

    # --- Proceed to API Check ---
    if not groq_client: 
        if cached_analysis: 
             return {
                "summary": json.loads(cached_analysis.content),
                "metadata": {
                    "quarter": cached_analysis.quarter,
                    "year": cached_analysis.year,
                    "last_api_check": cached_analysis.last_api_check.isoformat()
                }
            }
        return {"error": "Missing GROQ_API_KEY on server."}

    # Fetch latest transcript metadata from Data API
    data_pkg = get_transcript(ticker)
    
    if not data_pkg or not data_pkg.get('transcript'):
        if cached_analysis:
             return {
                "summary": json.loads(cached_analysis.content),
                "metadata": {
                    "quarter": cached_analysis.quarter,
                    "year": cached_analysis.year,
                    "last_api_check": cached_analysis.last_api_check.isoformat()
                }
            }
        return {"error": "Could not retrieve transcript (Premium Access Required)"}

    # Compare with Cache
    transcript = data_pkg['transcript']
    new_quarter = data_pkg.get('quarter', 'N/A')
    new_year = data_pkg.get('year', 'N/A')
    
    if cached_analysis:
        if new_quarter == cached_analysis.quarter and new_year == cached_analysis.year:
            # Same report, update timestamp
            cached_analysis.last_api_check = datetime.utcnow()
            db.commit()
            return {
                "summary": json.loads(cached_analysis.content),
                "metadata": {
                    "quarter": cached_analysis.quarter,
                    "year": cached_analysis.year,
                    "last_api_check": cached_analysis.last_api_check.isoformat()
                }
            }

    # --- If New Report: Run AI Analysis ---
    if len(transcript) > 50000:
        transcript = transcript[:50000] + "...(truncated)"
    
    prompt = f"""
    Role: You are a Senior Wall Street Analyst (CFA) explaining results to a Retail Investor.
    Task: Analyze this earnings call transcript for {ticker}.

    CONTEXT:
    - The "Prepared Remarks" are the scripted, optimistic pitch from the CEO/CFO.
    - The "Q&A Session" is where the real truth comes out (analysts drilling for weakness).

    INSTRUCTIONS:
    1.  **Separate your analysis** into two distinct sections: "Prepared Remarks" and "Q&A".
    2.  **Persona**: Be sophisticated but accessible. Use clean, plain English. Explain *why* a metric matters if it's technical.
    3.  **Tone**: Objective, slightly skeptical (don't just believe the CEO hype), focused on *implication*.

    OUTPUT FORMAT (JSON ONLY):
    {{
      "prepared_remarks": {{
        "sentiment": "Bullish|Bearish|Neutral",
        "summary": "2-3 sentences capturing the main strategic narrative.",
        "key_points": ["Bullet 1 (Strategy)", "Bullet 2 (Growth)", "Bullet 3 (Guidance)"]
      }},
      "qa_session": {{
        "sentiment": "Bullish|Bearish|Neutral",
        "summary": "2-3 sentences on the tone of the questions and management's ability to answer.",
        "revelations": ["Bullet 1 (A hidden risk exposed)", "Bullet 2 (Clarification on guidance)", "Bullet 3"]
      }},
      "verdict": {{
        "rating": "Buy|Hold|Sell",
        "reasoning": "One final decisive sentence for the retail investor."
      }}
    }}
    
    Transcript:
    {transcript}
    """
    
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a Senior CFA Analyst. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2, # Slightly higher for "persona" but still low for JSON
            response_format={"type": "json_object"}
        )
        
        text = completion.choices[0].message.content
        data = json.loads(text)
        
        # Save to DB
        # Check if we already have this specific quarter/year to avoid unique constraint error
        # (Though logic above suggests we typically wouldn't, unless partial race condition or manual DB insert)
        existing_exact = db.query(EarningsAnalysis).filter(
            EarningsAnalysis.ticker == ticker,
            EarningsAnalysis.quarter == new_quarter,
            EarningsAnalysis.year == new_year
        ).first()
        
        if existing_exact:
            existing_exact.content = json.dumps(data)
            existing_exact.last_api_check = datetime.utcnow()
        else:
            new_analysis = EarningsAnalysis(
                ticker=ticker,
                quarter=new_quarter,
                year=new_year,
                content=json.dumps(data),
                last_api_check=datetime.utcnow()
            )
            db.add(new_analysis)
            
        db.commit()
            
        return {
            "summary": data,
            "metadata": {
                "quarter": new_quarter,
                "year": new_year,
                "last_api_check": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"AI Processing Failed (Groq): {str(e)}"}
