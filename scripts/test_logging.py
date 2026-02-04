
import requests
import time

BASE_URL = "http://localhost:8000"

def trigger_logs():
    print("🚀 Triggering Logging Events...")
    
    # 1. Success Case
    print(f"\n[1] Requesting AAPL (Should show 'Coordinator: Created single Ticker...')")
    try:
        requests.get(f"{BASE_URL}/api/data/analysis/AAPL")
        print("✅ Request Sent.")
    except Exception as e:
        print(f"❌ Failed: {e}")

    # 2. Failure Case
    print(f"\n[2] Requesting INVALID_TICKER_XYZ (Should show 'Coordinator [Info] failed...')")
    try:
        requests.get(f"{BASE_URL}/api/data/analysis/INVALID_TICKER_XYZ")
        print("✅ Request Sent.")
    except Exception as e:
        print(f"❌ Failed: {e}")

    print("\n📋 INSTRUCTIONS:")
    print("1. Look at the terminal window where you are running './run_local.sh'")
    print("2. You should see new colored log entries corresponding to these requests.")

if __name__ == "__main__":
    trigger_logs()
