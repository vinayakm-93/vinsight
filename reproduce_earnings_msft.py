import os
import sys
from dotenv import load_dotenv

# Load env before imports that might use env vars
load_dotenv('backend/.env')

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.earnings import get_transcript_data
import json

ticker = "MSFT"
print(f"Testing earnings fetch for {ticker}...")

data = get_transcript_data(ticker)

if data:
    print("SUCCESS: Found transcript data.")
    print(f"URL: {data['url']}")
    print(f"Quarter: {data['quarter']}")
    print(f"Year: {data['year']}")
    print(f"Text length: {len(data['transcript'])}")
else:
    print("FAILURE: Could not fetch transcript data.")
