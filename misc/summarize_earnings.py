import os
import requests
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_NINJAS_KEY = os.getenv("API_NINJAS_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not API_NINJAS_KEY or not GEMINI_API_KEY:
    print("Error: Missing API Keys in .env file.")
    print("Please ensure API_NINJAS_KEY and GEMINI_API_KEY are set.")
    # Exit or continue with prompt? Better to exit for a tool.
    # exit(1) 

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')

def get_transcript(ticker):
    """Fetches earnings transcript from API Ninjas."""
    api_url = f'https://api.api-ninjas.com/v1/earningstranscript?ticker={ticker}'
    try:
        response = requests.get(api_url, headers={'X-Api-Key': API_NINJAS_KEY})
        if response.status_code == 200:
            data = response.json()
            if not data:
                return None # No data found
            return data[0].get('transcript')
        elif response.status_code == 403: # Check specifically for this if free tier limit
             print("Ticker not in S&P 100 (Free Tier Limit). Please try a major stock like AAPL, MSFT, or GOOG.")
             return None
        else:
            print(f"Error fetching transcript: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception fetching transcript: {e}")
        return None

def summarize_call(ticker):
    """Main execution flow."""
    print(f"\n🎧 Fetching Earnings Call Transcript for {ticker}...")
    transcript = get_transcript(ticker)
    
    if not transcript:
        print("❌ Could not retrieve transcript.")
        return

    # Truncate if too long (handling token limits conservatively)
    # API Ninjas transcripts can be huge. prioritizing first 50% as requested.
    if len(transcript) > 30000:
        print(f"⚠️ Transcript is long ({len(transcript)} chars). Truncating to first 15,000 characters (Management Discussion)...")
        transcript = transcript[:15000]
    
    print("🤖 Analyzing with Gemini (Hedge Fund Analyst Persona)...")
    
    prompt = f"""
    You are a hedge fund analyst. Read this earnings call transcript for {ticker}.
    Output strictly 3 sections: 
    1. 'The Good (Bullish)'
    2. 'The Bad (Bearish)'
    3. 'The Ugly (Risk Factors)'
    
    Use bullet points. Be concise and focus on financial metrics, guidance, and strategic shifts.
    
    Transcript:
    {transcript}
    """
    
    try:
        response = model.generate_content(prompt)
        print("\n" + "="*50)
        print(f"📊 EARNINGS SUMMARY: {ticker}")
        print("="*50)
        print(response.text)
        print("\n" + "="*50)
    except Exception as e:
        print(f"Error generating summary: {e}")

if __name__ == "__main__":
    while True:
        user_input = input("\nEnter Ticker Symbol (or 'q' to quit): ").strip().upper()
        if user_input == 'Q':
            break
        if user_input:
            summarize_call(user_input)
