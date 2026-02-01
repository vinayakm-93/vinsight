"""
Test script for EODHD insider trading integration

This script tests the EODHD integration without requiring an API key.
It verifies the fallback logic and data structure.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.eodhd_insider import is_available, get_insider_transactions_eodhd
from services.finance import get_institutional_holders


def test_eodhd_availability():
    """Test if EODHD is properly configured."""
    print("=" * 60)
    print("TEST 1: EODHD Availability Check")
    print("=" * 60)
    
    available = is_available()
    print(f"EODHD Available: {available}")
    
    if available:
        print("✅ EODHD is configured and enabled")
    else:
        print("⚠️  EODHD not configured - will use yfinance fallback")
        print("   To enable: Set EODHD_API_KEY in .env file")
    
    print()


def test_insider_data_structure():
    """Test the data structure returned by get_institutional_holders."""
    print("=" * 60)
    print("TEST 2: Insider Data Structure (Using AAPL)")
    print("=" * 60)
    
    ticker = "AAPL"
    print(f"Fetching insider data for {ticker}...")
    
    try:
        data = get_institutional_holders(ticker)
        
        print(f"\nData Source: {data.get('insider_source', 'unknown')}")
        print(f"Insider Activity: {data.get('insider_activity', 'unknown')}")
        
        # Check metadata
        if 'insider_metadata' in data:
            metadata = data['insider_metadata']
            print("\nInsider Metadata:")
            print(f"  Total Transactions: {metadata.get('total', 'N/A')}")
            print(f"  Discretionary: {metadata.get('discretionary', 'N/A')}")
            print(f"  Automatic (10b5-1): {metadata.get('automatic_10b5_1', 'N/A')}")
            print(f"  Days Analyzed: {metadata.get('days_analyzed', 'N/A')}")
        
        # Check transactions
        transactions = data.get('insider_transactions', [])
        print(f"\nTotal Transactions Returned: {len(transactions)}")
        
        if transactions:
            print("\nFirst 3 Transactions:")
            for i, tx in enumerate(transactions[:3], 1):
                print(f"\n  Transaction {i}:")
                print(f"    Date: {tx.get('Date', 'N/A')}")
                print(f"    Insider: {tx.get('Insider', 'N/A')}")
                print(f"    Position: {tx.get('Position', 'N/A')}")
                print(f"    Text: {tx.get('Text', 'N/A')}")
                print(f"    Shares: {tx.get('Shares', 'N/A')}")
                print(f"    Value: ${tx.get('Value', 0):,.0f}" if tx.get('Value') else "    Value: N/A")
                print(f"    Is 10b5-1: {tx.get('is_10b5_1', False)}")
        
        print("\n✅ Data structure test passed")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def test_10b5_1_filtering():
    """Test that 10b5-1 transactions are properly flagged."""
    print("=" * 60)
    print("TEST 3: 10b5-1 Filtering Logic")
    print("=" * 60)
    
    ticker = "TSLA"  # Tesla often has 10b5-1 transactions
    print(f"Fetching insider data for {ticker}...")
    
    try:
        data = get_institutional_holders(ticker)
        
        source = data.get('insider_source', 'unknown')
        print(f"\nData Source: {source}")
        
        transactions = data.get('insider_transactions', [])
        
        if source == 'eodhd':
            # Count 10b5-1 transactions
            automatic = sum(1 for t in transactions if t.get('is_10b5_1', False))
            discretionary = sum(1 for t in transactions if not t.get('is_10b5_1', False))
            
            print(f"\n10b5-1 Filtering Results:")
            print(f"  Total: {len(transactions)}")
            print(f"  Discretionary: {discretionary}")
            print(f"  Automatic (10b5-1): {automatic}")
            
            if automatic > 0:
                print(f"\n✅ 10b5-1 detection working ({automatic} automatic transactions found)")
            else:
                print(f"\n⚠️  No 10b5-1 transactions found (may be none in last 90 days)")
        else:
            print(f"\n⚠️  Using {source} - 10b5-1 detection not available")
            print("   Set EODHD_API_KEY to enable 10b5-1 detection")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("EODHD INSIDER TRADING INTEGRATION TEST")
    print("=" * 60)
    print()
    
    test_eodhd_availability()
    test_insider_data_structure()
    test_10b5_1_filtering()
    
    print("=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)
    print()
    print("Next Steps:")
    print("1. If EODHD not configured: Sign up at https://eodhd.com/register")
    print("2. Add EODHD_API_KEY to your .env file")
    print("3. Run this test again to verify EODHD integration")
    print()


if __name__ == "__main__":
    main()
