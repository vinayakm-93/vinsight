# Developer Guide: Manual Stock Scoring

This guide explains how to manually test the VinSight Scoring Engine script without the full web interface.

## 1. Manual Evaluation Script
To evaluate a stock manually, you can use the `vinsight_scorer.py` script directly.

### Template Code
```python
from vinsight_scorer import VinSightScorer, StockData, Fundamentals, Technicals, Sentiment, Projections

new_stock = StockData(
    ticker="AAPL",
    # Fundamentals
    fundamentals=Fundamentals(
        inst_ownership=60.5,
        pe_ratio=28.0,
        analyst_upside=10.0
    ),
    # Technicals
    technicals=Technicals(
        price=150.0,
        sma50=145.0,
        sma200=140.0,
        rsi=45.0,
        momentum_label="Bullish",
        volume_trend="Price Rising + Vol Rising"
    ),
    # Sentiment
    sentiment=Sentiment(
        sentiment_label="Neutral",
        insider_activity="Mixed/Minor Selling"
    ),
    # Projections
    projections=Projections(
        monte_carlo_p50=160.0,
        current_price=150.0,
        risk_reward_gain_p90=20.0,
        risk_reward_loss_p10=10.0
    )
)

# Run Evaluation
scorer = VinSightScorer()
result = scorer.evaluate(new_stock)
scorer.print_report(new_stock, result)
```

### Running the Evaluation
```bash
cd backend/services
python3 vinsight_scorer.py
```

## 2. API Testing
For testing endpoints directly:
- **FastAPI Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Monitoring**: Check `backend.log` for real-time API request tracing.
- **[Earnings Scraper Guide](./DEV_SCRAPER.md)**: Architecture of the DIY transcript fetcher.
