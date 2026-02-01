# Features of VinSight

## 1. Real-Time Dashboard
- **Candlestick Chart**: Custom-built using `lightweight-charts`. Shows Open, High, Low, Close data.
- **Volume Bars**: Visual representation of trading activity.
- **Timeframes**: Switch between Daily, Weekly, and Intraday views.

## 2. Artificial Intelligence (v5.1)
- **Sentiment Analysis** (Hybrid Cascade):
    - **Alpha Vantage** (Primary): Pre-scored sentiment with article summaries.
    - **Groq (Llama 3.3 70B)** (Fallback): Deep headline analysis with spin detection.
    - **TextBlob** (Emergency): Dictionary-based fallback if APIs unavailable.
- **Finnhub Insider Sentiment**: MSPR (Monthly Share Purchase Ratio) from SEC filings.
- **Insider Activity (v6.7.2)**: 
    - **Discretionary Filter**: Distinguishes "Real" trades from "Automatic" (10b5-1) plans.
    - **Smart Signal**: 90-day sentiment score based purely on executive conviction.
- **Spin Detection**: Bearish keyword list catches positive framing of negative news.
- **AI Analyst**: Automated natural language summary of company financial health.

## 3. VinSight Score (v7.3 - Wealth Manager Edition)
A sophisticated "Fundamental Purist" algorithm designed for quarterly investors:
- **Fundamentals (100% of Score)**: Valuation (PEG/Forward PE), Quality (Margins), Efficiency (ROE/ROA), Solvency (Debt/Current Ratio).
- **Risk Gates (Penalties)**: 
    - **Trend Gate**: -15 pts if Price < SMA200 (Downtrend).
    - **Projection Gate**: -15 pts if Monte Carlo P10 predicts >15% loss.
- **Dynamic Benchmarking**: Targets adjust automatically based on sector (e.g., Tech vs. Banks).
- **Optimization**: "Deep Sentiment" disabled for instant loading; sentiment is display-only.
- [Read Full Logic](./VINSIGHT_SCORER_V7_LOGIC.md)

**Dynamic Benchmarking v7.4**:
- Consolidated **10 Wealth Manager Themes** (High Growth Tech, Financials, etc.).
- **Market Reference**: Auto-benchmarks against S&P 500 averages.
- Automatic precise mapping of 200+ sub-industries to these 10 themes.

**Outlooks (3m/6m/12m)**:
- **3 Months**: Technical/Momentum focus (RSI, SMA50, Sentiment, Beta)
- **6 Months**: Valuation/Growth focus (PEG, P/E, SMA200, Earnings Growth)
- **12 Months**: Quality/Fundamental focus (Margins, Debt, 52W Range, Dividends)

**Result**: Score 0-100 with ratings (Strong Buy ≥80 / Buy ≥65 / Hold ≥45 / Sell <45).

## 4. Projections Tab (Monte Carlo Engine)
- **Scenario Cards**: Bear (P10), Base (P50), Bull (P90) price targets displayed at top
- **Risk Metrics**: Expected Return, Value at Risk (95%), Probability of Loss, Annualized Volatility
- **Probability Analysis**: Likelihood of hitting various price targets (+25%, +10%, break-even, -10%, -25%)
- **Return Distribution**: Interactive histogram showing the distribution of simulated returns
- **Analyst Consensus**: Yahoo Finance target prices (low/mean/high), number of covering analysts, and recommendation
- **Duration Selector**: 90-day projection window with manual rerun capability

## 5. AI Sentiment Tab
- **On-Demand Deep Analysis**: Automatic sentiment analysis when tab is clicked
- **Finnhub News Integration**: Real-time news with sentiment scoring
- **Groq AI Reasoning**: Deep headline analysis with spin detection
- **Insider Activity**: MSPR (Monthly Share Purchase Ratio) from SEC filings

## 6. Smart Alerts
- **Price Alerts**: "Tell me if AAPL goes above $200".
- **Sentiment Alerts**: "Warn me if news turns negative".
- **Delivery**: Alerts are sent via Email (SMTP).

## 7. Guest Mode
- **No Login Required**: Users can try the app without creating an account.
- **LocalStorage Persistence**: Guest watchlist is saved in browser storage.
- **Default Stocks**: Comes pre-loaded with popular tickers (AAPL, NVDA, SPY, etc.).

## 8. Security
- **JWT Authentication**: Secure login system.
- **Password Hashing**: PBKDF2 hashing for user passwords.
- **Email Verification**: 6-digit code sent before account creation.
- **Rate Limiting**: API endpoints protected against abuse.
