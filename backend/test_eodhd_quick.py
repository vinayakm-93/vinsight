"""Quick test to verify EODHD API is working"""
import os
from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.insert(0, '/Users/vinayak/Documents/Antigravity/Project 1/backend')

from services.eodhd_insider import is_available, get_insider_transactions_eodhd

print("=" * 60)
print("EODHD LIVE API TEST")
print("=" * 60)

# Check availability
print(f"\nEODHD_API_KEY set: {bool(os.getenv('EODHD_API_KEY'))}")
print(f"EODHD_API_KEY value: {os.getenv('EODHD_API_KEY')[:20]}...")
print(f"EODHD_ENABLED: {os.getenv('EODHD_ENABLED')}")
print(f"is_available(): {is_available()}")

if is_available():
    print("\n✅ EODHD is configured!")
    print("\nTesting with AAPL...")
    
    data = get_insider_transactions_eodhd("AAPL")
    
    if data:
        print(f"\n✅ SUCCESS! Got data from EODHD:")
        print(f"  Total transactions: {data['total_count']}")
        print(f"  Discretionary: {data['discretionary_count']}")
        print(f"  Automatic (10b5-1): {data['automatic_count']}")
        print(f"  Days analyzed: {data['days_analyzed']}")
        
        if data['transactions']:
            print(f"\n  First transaction:")
            tx = data['transactions'][0]
            print(f"    Date: {tx['Date']}")
            print(f"    Insider: {tx['Insider']}")
            print(f"    Type: {tx['Text']}")
            print(f"    Is 10b5-1: {tx['is_10b5_1']}")
    else:
        print("\n❌ EODHD returned no data")
else:
    print("\n❌ EODHD not available")
    print("Check:")
    print("  1. EODHD_API_KEY in .env")
    print("  2. EODHD_ENABLED=true")
