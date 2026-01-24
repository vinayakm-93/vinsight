
import time
import numpy as np
import pandas as pd

# Mock Data
history = [{'Close': 100 + i + np.random.normal(0, 1)} for i in range(252)] # 1 year data

# --- Current Implementation (Slow) ---
def run_monte_carlo_old(history, days=90, simulations=10000):
    if not history: return {}
    df = pd.DataFrame(history)
    close_prices = pd.to_numeric(df['Close'])
    last_price = close_prices.iloc[-1]
    returns = close_prices.pct_change().dropna()
    mu = returns.mean()
    sigma = returns.std()
    
    simulation_results = []
    
    start_time = time.time()
    for _ in range(simulations):
        prices = [last_price]
        for _ in range(days):
            shock = np.random.normal(mu, sigma)
            price = prices[-1] * (1 + shock)
            prices.append(price)
        simulation_results.append(prices)
    end_time = time.time()
    
    print(f"Old Implementation Time: {end_time - start_time:.4f} seconds")
    return simulation_results

# --- New Implementation (Fast) ---
def run_monte_carlo_vectorized(history, days=90, simulations=10000):
    if not history: return {}
    df = pd.DataFrame(history)
    close_prices = pd.to_numeric(df['Close'])
    last_price = close_prices.iloc[-1]
    returns = close_prices.pct_change().dropna()
    mu = returns.mean()
    sigma = returns.std()
    
    start_time = time.time()
    
    # Vectorized Logic
    # Generate all shocks at once: Shape (simulations, days)
    shocks = np.random.normal(mu, sigma, (simulations, days))
    
    # Calculate price factors: (1 + shock)
    price_factors = 1 + shocks
    
    # Cumulative product to get path multipliers
    price_paths = np.cumprod(price_factors, axis=1)
    
    # Multiply by last price to get actual prices
    final_paths = last_price * price_paths
    
    # Prepend last_price to each path (optional, but current impl does it)
    # For speed, we might skip full path reconstruction if only stats are needed,
    # but to be fair, let's just measure the calculation.
    
    end_time = time.time()
    
    print(f"Vectorized Time: {end_time - start_time:.4f} seconds")
    return final_paths

print(f"Running Benchmark with {10000} simulations over {90} days...")
run_monte_carlo_old(history)
run_monte_carlo_vectorized(history)
