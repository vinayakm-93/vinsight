import json
import os
import sys

def upgrade_benchmarks():
    """
    Upgrades backend/config/sector_benchmarks.json with sector-specific
    thresholds for 'fcf_yield_strong' and 'eps_surprise_huge'.
    """
    
    config_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'config', 'sector_benchmarks.json')
    config_path = os.path.abspath(config_path)
    
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}")
        return

    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading config: {e}")
        return

    sectors = data.get('sectors', {})
    
    # Logic Map
    # High Growth: FCF 4%, EPS 15%
    high_growth = ['Technology', 'Software', 'Semiconductors', 'AI/ML', 'Cloud/SaaS', 'Cybersecurity', 'Fintech', 'Biotech', 'EV/Clean Energy']
    
    # High Yield: FCF 7-8%, EPS 5%
    high_yield = ['Energy', 'Utilities', 'REITs', 'Banks', 'Insurance', 'Basic Materials', 'Real Estate']
    
    # Defensive: FCF 6%, EPS 8%
    defensive = ['Consumer Defensive', 'Healthcare', 'Pharma']
    
    # Cyclical/Consumer: Defaults (FCF 5%, EPS 10%)
    
    updated_count = 0
    
    for sector_name, metrics in sectors.items():
        # Determine appropriate values
        if sector_name in high_growth:
            fcf_target = 0.04
            eps_target = 0.15
        elif sector_name in high_yield:
            # Banks/Insurance usually have weird FCF, but we'll set high bar for "Cash Cow" status if used
            if sector_name in ['Banks', 'Insurance']:
                 fcf_target = 0.08 # Very high bar
            else:
                 fcf_target = 0.07 # 7% yield is strong for Energy/REITs
            eps_target = 0.05
        elif sector_name in defensive:
            fcf_target = 0.06
            eps_target = 0.08
        else:
            # Default
            fcf_target = 0.05
            eps_target = 0.10
            
        # Update metrics if missing or just overwrite to ensure consistency?
        # Plan said "inject", essentially overwrite/update.
        metrics['fcf_yield_strong'] = fcf_target
        metrics['eps_surprise_huge'] = eps_target
        updated_count += 1
        
    # Update Metadata
    data['last_updated'] = "2026-01-23"
    data['version'] = "2026-Q1" # Bump version
    
    # Ensure defaults are correct
    if 'defaults' in data:
        data['defaults']['fcf_yield_strong'] = 0.05
        data['defaults']['eps_surprise_huge'] = 0.10

    # Write back
    try:
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Successfully upgraded {updated_count} sectors in {config_path}")
    except Exception as e:
        print(f"Error writing config: {e}")

if __name__ == "__main__":
    upgrade_benchmarks()
