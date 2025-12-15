# How to Add Stocks to VinSight Scorer

To evaluate different stocks using the **VinSight Scorer**, you need to edit the `vinsight_scorer.py` script.

## Steps

1. **Open `vinsight_scorer.py`** in your code editor.
2. **Locate the `run_test_case` function** or create a new main execution block.
3. **Instantiate `StockData`** with your stock's specific metrics.

### Example Template

```python
new_stock = StockData(
    ticker="AAPL",
    
    # Fundamentals
    fundamentals=Fundamentals(
        inst_ownership=60.5,  # Percentage
        pe_ratio=28.0,
        analyst_upside=10.0   # Percentage
    ),
    
    # Technicals
    technicals=Technicals(
        price=150.0,
        sma50=145.0,
        sma200=140.0,
        rsi=45.0,
        momentum_label="Bullish",  # Options: "Bullish", "Bearish"
        volume_trend="Price Rising + Vol Rising" # Options: "Price Rising + Vol Rising", "Price Rising + Vol Falling", "Price Falling + Vol Rising", "Weak/Mixed"
    ),
    
    # Sentiment
    sentiment=Sentiment(
        sentiment_label="Neutral", # Options: "Positive", "Neutral", "Negative"
        insider_activity="Mixed/Minor Selling" # Options: "Net Buying", "Mixed/Minor Selling", "Heavy Selling"
    ),
    
    # Projections
    projections=Projections(
        monte_carlo_p50=160.0,
        current_price=150.0,
        risk_reward_gain_p90=20.0, # Dollar amount to P90
        risk_reward_loss_p10=10.0  # Dollar amount to P10
    )
)

# Run Evaluation
scorer = VinSightScorer()
result = scorer.evaluate(new_stock)
scorer.print_report(new_stock, result)
```

## Running the Script

Open your terminal and run:

```bash
python3 vinsight_scorer.py
```
