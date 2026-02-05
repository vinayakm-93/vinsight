import os
import sys
from dotenv import load_dotenv

# Load env but we will override SERPER_API_KEY
load_dotenv('backend/.env')
os.environ['SERPER_API_KEY'] = "" # Force empty

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.earnings import get_transcript_data
import json

ticker = "MSFT"
print(f"Testing earnings fetch for {ticker} WITHOUT Serper...")

data = get_transcript_data(ticker)

if data:
    print("SUCCESS: Found transcript data via fallback.")
    print(f"URL: {data['url']}")
else:
    print("FAILURE: Could not fetch transcript data via fallback.")
