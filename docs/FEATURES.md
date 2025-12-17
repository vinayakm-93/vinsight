# Features of VinSight

## 1. Real-Time Dashboard
- **Candlestick Chart**: Custom-built using `lightweight-charts`. Shows Open, High, Low, Close data.
- **Volume Bars**: Visual representation of trading activity.
- **Timeframes**: Switch between Daily, Weekly, and Intraday views.

## 2. Artificial Intelligence (v2.5)
- **Sentiment Analysis** (Hybrid Cascade):
    - **Alpha Vantage** (Primary): Pre-scored sentiment with article summaries.
    - **Groq (Llama 3.3 70B)** (Fallback): Deep headline analysis with spin detection.
    - **TextBlob** (Emergency): Dictionary-based fallback if APIs unavailable.
- **Spin Detection**: Bearish keyword list catches positive framing of negative news.
- **AI Analyst**: Automated natural language summary of company financial health.

## 3. VinSight Score (v2.5 - Industry Benchmarks)
A proprietary algorithm combining **4 pillars (100 pts)**:
- **Fundamentals (30 pts)**: PEG < 1.0 (Peter Lynch), P/E < 15 (Graham), sector-adjusted growth.
- **Technicals (30 pts)**: RSI 30/70 thresholds, SMA trends, volume conviction.
- **Sentiment (20 pts)**: News sentiment + insider activity (detects Cluster Selling).
- **Projections (20 pts)**: Monte Carlo P50 upside + risk/reward ratio.
**Result**: Score 0-100 with ratings (Strong Buy/Buy/Hold/Weak Hold/Sell).

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
