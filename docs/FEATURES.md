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
- **Spin Detection**: Bearish keyword list catches positive framing of negative news.
- **AI Analyst**: Automated natural language summary of company financial health.

## 3. VinSight Score (v6.0 - Rebalanced for Retail Investors)
A proprietary algorithm combining **4 pillars (100 pts)** with **partial credits everywhere**:
- **Fundamentals (55 pts)**: Valuation (12), Earnings Growth (10), Profit Margins (10), Debt Health (8), Institutional Ownership (8), Smart Money Flow (7).
- **Technicals (15 pts)**: SMA distance scoring, RSI optimal zone (50-65), volume conviction.
- **Sentiment (15 pts)**: News sentiment (8 pts) + Finnhub insider MSPR (7 pts).
- **Projections (15 pts)**: Monte Carlo P50 upside (9 pts) + risk/reward ratio (6 pts).

**Industry Peer Values** (displayed in Fundamentals expansion):
- Shows sector-specific benchmarks: PEG fair value, growth threshold, margin threshold, safe debt level.
- Dynamically fetched from `/api/data/sector-benchmarks`.

**Result**: Score 0-100 with ratings (Strong Buy ≥80 / Buy ≥65 / Hold ≥45 / Sell <45).

## 4. Smart Alerts
- **Price Alerts**: "Tell me if AAPL goes above $200".
- **Sentiment Alerts**: "Warn me if news turns negative".
- **Delivery**: Alerts are sent via Email (SMTP).

## 5. Guest Mode
- **No Login Required**: Users can try the app without creating an account.
- **LocalStorage Persistence**: Guest watchlist is saved in browser storage.
- **Default Stocks**: Comes pre-loaded with popular tickers (AAPL, NVDA, SPY, etc.).

## 6. Security
- **JWT Authentication**: Secure login system.
- **Password Hashing**: PBKDF2 hashing for user passwords.
- **Email Verification**: 6-digit code sent before account creation.
- **Rate Limiting**: API endpoints protected against abuse.
