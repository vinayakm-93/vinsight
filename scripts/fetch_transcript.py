import os
import requests
from dotenv import load_dotenv
import sys

# Load env vars from project root
# Hardcode path for reliability in this environment
env_path = "/Users/vinayak/Documents/Antigravity/Project 1/.env"
print(f"Loading .env from: {env_path}")
load_dotenv(env_path)

API_NINJAS_KEY = os.getenv("API_NINJAS_KEY")

def get_transcript(ticker):
    if not API_NINJAS_KEY:
        print("Error: API_NINJAS_KEY not found in environment variables.")
        return

    print(f"Fetching transcript for {ticker}...")
    api_url = f'https://api.api-ninjas.com/v1/earningstranscript?ticker={ticker}'
    
    try:
        response = requests.get(api_url, headers={'X-Api-Key': API_NINJAS_KEY})
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                transcript_data = data[0]
                quarter = transcript_data.get('quarter')
                year = transcript_data.get('year')
                transcript = transcript_data.get('transcript')
                
                print(f"Successfully fetched {ticker} Q{quarter} {year} transcript.")
                print(f"Length: {len(transcript)} characters")
                
                filename = f"{ticker}_Q{quarter}_{year}_transcript.txt"
                with open(filename, "w") as f:
                    f.write(transcript)
                
                print(f"Saved to {filename}")
                print("\nFirst 500 characters preview:\n")
                print(transcript[:500] + "...")
            else:
                print("No transcript data found for this ticker.")
        else:
            print(f"Error: API returned status code {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    ticker = "AAPL"
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
    get_transcript(ticker)
