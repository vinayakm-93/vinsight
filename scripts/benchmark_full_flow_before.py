
import time
import sys
import os

# Add backend to sys.path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services import finance, analysis, simulation

# Mock Data Fetching to avoid network noise? 
# Or better, let's measure REAL execution time including the slow simulation.
# We want to measure the processing time.

def benchmark_current_state(ticker="AAPL"):
    print(f"Benchmarking Current State for {ticker}...")
    
    start_time = time.time()
    
    # 1. Fetch History (Frontend calls this)
    history = finance.get_stock_history(ticker, period="1mo", interval="1d")
    
    # 2. Fetch Stock Details (Frontend calls this)
    details = finance.get_stock_info(ticker)
    
    # 3. Fetch Analysis (Frontend calls this)
    # This internally fetches history (AGAIN), info (AGAIN), news, institutional, 
    # and runs current (slow) simulation.
    # Note: We need to mock the concurrent execution or just run it sequentially 
    # to measure CPU time. Since `data.py` does valid concurrent calls, 
    # we should try to replicate `data.py` logic or just call the route handler if possible?
    # Calling the route handler is best but it's an async FastAPI route? 
    # No, `def get_technical_analysis` in `data.py` is synchronous def.
    
    # Let's import the route handler directly to be accurate to what the backend does.
    from routes.data import get_technical_analysis
    
    analysis_result = get_technical_analysis(ticker, period="2y", interval="1d")
    
    end_time = time.time()
    
    print(f"Current Full Flow Time: {end_time - start_time:.4f} seconds")

if __name__ == "__main__":
    try:
        benchmark_current_state()
    except Exception as e:
        print(f"Error: {e}")
