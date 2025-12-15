import numpy as np
import pandas as pd
from typing import List, Dict

def run_monte_carlo(history: List[Dict], days: int = 30, simulations: int = 1000) -> Dict:
    """
    Runs Monte Carlo simulation for future price paths.
    """
    if not history:
        return {}
        
    df = pd.DataFrame(history)
    close_prices = pd.to_numeric(df['Close'])
    last_price = close_prices.iloc[-1]
    
    # Calculate daily returns stats
    returns = close_prices.pct_change().dropna()
    mu = returns.mean()
    sigma = returns.std()
    
    # Simulation
    simulation_results = []
    
    for _ in range(simulations):
        prices = [last_price]
        for _ in range(days):
            shock = np.random.normal(mu, sigma)
            price = prices[-1] * (1 + shock)
            prices.append(price)
        simulation_results.append(prices)
        
    # Aggregate results for plotting (e.g., 10th, 50th, 90th percentiles)
    sim_array = np.array(simulation_results)
    
    future_days = list(range(1, days + 1))
    p10 = np.percentile(sim_array, 10, axis=0)[1:].tolist()
    p50 = np.percentile(sim_array, 50, axis=0)[1:].tolist()
    p90 = np.percentile(sim_array, 90, axis=0)[1:].tolist()
    
    # Calculate Summary Metrics
    final_prices = sim_array[:, -1]
    mean_price = np.mean(final_prices)
    expected_return_pct = ((mean_price - last_price) / last_price) * 100
    
    # Value at Risk (95% confidence) - Potential loss
    p05 = np.percentile(final_prices, 5)
    risk_var = max(0, last_price - p05)
    
    return {
        "days": future_days,
        "paths": simulation_results[:50],  # Return first 50 paths for visualization
        "p10": p10,
        "p50": p50,
        "p90": p90,
        "mean_price": mean_price,
        "expected_return": expected_return_pct,
        "risk_var": risk_var
    }
