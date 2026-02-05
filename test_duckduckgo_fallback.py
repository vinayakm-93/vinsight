
import os
import sys
from unittest.mock import patch

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

import services.earnings

# Mock SERPER_API_KEY to None in the module directly
with patch('services.earnings.SERPER_API_KEY', None):
    ticker = 'MSFT'
    print(f"Testing DuckDuckGo fallback for {ticker} (Serper mocked to None)...")
    url = services.earnings.search_transcript_url(ticker)
    if url:
        print(f"SUCCESS: Found URL via fallback: {url}")
    else:
        print("FAILURE: Fallback failed to find URL.")
