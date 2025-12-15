import os
import requests
import json
from groq import Groq
from datetime import datetime, timedelta

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
    # print(f"DEBUG: Fetching transcript for {ticker} from {api_url}")
    
    try:
        response = requests.get(api_url, headers={'X-Api-Key': API_NINJAS_KEY})
        # print(f"DEBUG: API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if not data:
                # print("DEBUG: API returned 200 but empty list (no transcript found).")
                return None 
            
            # print(f"DEBUG: Data type: {type(data)}")
            
            if isinstance(data, list) and len(data) > 0:
                item = data[0]
                return {
                    "transcript": item.get('transcript'),
                    "quarter": item.get('quarter'),
                    "year": item.get('year'),
                    "date": item.get('date')
                }
            elif isinstance(data, dict):
                return {
                    "transcript": data.get('transcript'),
                    "quarter": data.get('quarter'),
                    "year": data.get('year'),
                    "date": data.get('date')
                }
            else:
                 return None
        else:
            # print(f"DEBUG: Error fetching transcript: {response.status_code}")
            return None
    except Exception as e:
        print(f"DEBUG: Exception fetching transcript: {e}")
        return None

def analyze_earnings(ticker: str):
    """
    Fetches transcript and returns structured summary.
    Checks local cache first.
    Refreshes cache IF:
    1. Cache doesn't exist.
    2. Cache exists but 'last_api_check' was > 24 hours ago (Staleness Check).
       - In this case, we call the Data API to see if there is a NEW transcript.
       - If Data API shows same quarter/year, we just update 'last_api_check' (Cheap).
       - If Data API shows NEW quarter/year, we run the AI Analysis (Expensive).
    """
    # 1. Check Cache
    cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{ticker}_earnings.json")
    
    cached_data = None
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cached_data = json.load(f)
        except Exception as e:
            print(f"Error reading cache: {e}")

    # Check if we need to verify with API (Staleness Check)
    should_check_api = True
    if cached_data:
        last_check = cached_data.get("metadata", {}).get("last_api_check")
        if last_check:
            last_check_dt = datetime.fromisoformat(last_check)
            if datetime.now() - last_check_dt < timedelta(hours=24):
                should_check_api = False
    
    if not should_check_api and cached_data:
        # print(f"DEBUG: returning cached data (checked < 24h ago)")
        return cached_data

    # --- Proceed to API Check ---
    if not groq_client: # If we can't process, fallback to cache if exists
        if cached_data: return cached_data
        return {"error": "Missing GROQ_API_KEY on server."}

    # Fetch latest transcript metadata from Data API
    data_pkg = get_transcript(ticker)
    
    if not data_pkg or not data_pkg.get('transcript'):
        # API fail or no data. Return cache if we have it.
        if cached_data: return cached_data
        return {"error": "Could not retrieve transcript (or ticker not supported)"}

    # Compare with Cache
    transcript = data_pkg['transcript']
    new_quarter = str(data_pkg.get('quarter', 'N/A'))
    new_year = str(data_pkg.get('year', 'N/A'))
    call_date = data_pkg.get('date', 'N/A')
    
    # print(f"DEBUG: New Q: {new_quarter} Y: {new_year}")

    if cached_data:
        old_quarter = str(cached_data.get("metadata", {}).get("quarter", ""))
        old_year = str(cached_data.get("metadata", {}).get("year", ""))
        # print(f"DEBUG: Old Q: {old_quarter} Y: {old_year}")
        
        # If same report, just update the timestamp and return old AI summary
        if new_quarter == old_quarter and new_year == old_year:
            # print("DEBUG: Data API shows same report. Updating timestamp only.")
            cached_data["metadata"]["last_api_check"] = datetime.now().isoformat()
            try:
                with open(cache_file, "w") as f:
                    json.dump(cached_data, f, indent=2)
            except: pass
            return cached_data

    # --- If New Report: Run AI Analysis ---
    # print("DEBUG: New report found! Running AI Analysis...")

    # Truncate for Groq context window
    if len(transcript) > 50000:
        transcript = transcript[:50000] + "...(truncated)"
    
    prompt = f"""
    You are a hedge fund analyst. Read this earnings call transcript for {ticker}.
    Output strictly VALID JSON with 3 keys: 
    "bullish": [list of strings currently mentioned],
    "bearish": [list of strings currently mentioned],
    "risks": [list of strings currently mentioned]
    
    Do not use markdown formatting (no ```json). Just the raw JSON object.
    
    Transcript:
    {transcript}
    """
    
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a financial analyst helper outputting JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        text = completion.choices[0].message.content
        data = json.loads(text)
        result = {
            "summary": data,
            "metadata": {
                "quarter": new_quarter,
                "year": new_year,
                "date": call_date,
                "last_api_check": datetime.now().isoformat() # Timestamp of verification
            }
        }
        
        # Save to Cache
        try:
            with open(cache_file, "w") as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            print(f"Error saving cache: {e}")
            
        return result
        
    except Exception as e:
        return {"error": f"AI Processing Failed (Groq): {str(e)}"}
