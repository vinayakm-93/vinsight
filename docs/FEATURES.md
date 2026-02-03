# VinSight Features

## 1. Real-Time Dashboard
- **Candlestick Chart**: Professional charts built with `lightweight-charts`.
- **Intraday & Historical**: Switch between 1D, 1W, 1M, and 1Y views.
- **Watchlists**: Manage multiple portfolios with real-time price updates.

## 2. Artificial Intelligence Engine
- **Hybrid Sentiment Analysis**: Blended scores from Alpha Vantage, Finnhub, and Groq (Llama 3.3).
- **Deep Reasoning**: AI-driven "Thesis" and "Risk" analysis via Gemini 1.5 Pro.
- **Insider Intelligence**: 
    - **MSPR Tracking**: Monthly Share Purchase Ratio from SEC filings.
    - **10b5-1 Filter**: Distinguishes planned trades from discretionary executive action.
- **Spin Detection**: Automated detection of "positive framing" on negative financial news.
- **Senior Analyst Earnings AI**:
    - **Institutional Breakdown**: Separates the "Management Pitch" (Prepared Remarks) from the "Analyst Interrogation" (Q&A).
    - **CFA Persona**: AI acts as a Senior Wall Street Analyst translating complex calls for retail investors.
    - **Verdict Engine**: Explicit Buy/Hold/Sell rating based on transcript tone and unscripted revelations.

## 3. VinSight Score v9.0
Institutional-grade scoring with adaptive sector intelligence.
- **70/30 Weighted model** (Fundamentals/Technicals).
- **Dynamic Benchmarking**: Automatically adjusts "fair value" based on 12+ industry themes.
- **Veto Logic**: Automatic caps for insolvency or extreme overvaluation.
- **[Read Full Scoring Logic](./SCORING_ENGINE.md)**

## 4. Advanced Projections
- **Monte Carlo Scenarios**: Bull (P90), Base (P50), and Bear (P10) price targets.
- **Risk Assessment**: Value at Risk (VaR), Annualized Volatility, and Probability of hitting +25%/-25%.
- **Analyst Consensus**: Yahoo Finance target prices and recommendation trends.

## 5. Smart Alerts
- **Price Triggers**: Notification when a stock hits your target.
- **Execution**: Background monitoring via Cloud Scheduler.
- **Delivery**: Instant email notifications via SMTP.

## 6. Security & Persistence
- **Guest Mode**: Try the app with LocalStorage-persisted watchlists.
- **Secure Auth**: JWT-based login with email verification and hashed passwords.
- **[Read Security Documentation](./SECURITY.md)**

