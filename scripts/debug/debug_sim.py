import sys
import os
import random
import json

# Add backend directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.simulation import run_monte_carlo

# Mock 30 days of price history
history = []
price = 100.0
for i in range(30):
    price = price * (1 + random.uniform(-0.02, 0.02))
    history.append({"Date": f"2023-01-{i+1}", "Close": price})

# Run simulation
result = run_monte_carlo(history, days=5, simulations=20) # Small for readability

# Print structure
print(json.dumps({
    "inputs": {"start_price": history[-1]["Close"], "days": 5, "simulations": 20},
    "output_summary": {
        "mean_price": result["mean_price"],
        "expected_return": result["expected_return"],
        "risk_var_95": result["risk_var"]
    },
    "sample_paths_preview": [result["paths"][0], result["paths"][1]] # Show first 2 paths
}, indent=2))
