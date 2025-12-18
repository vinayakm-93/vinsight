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

## 3. VinSight Score (v6.1 - Retail Investor Focused)
A proprietary algorithm combining **4 pillars (100 pts)** with **partial credits everywhere**:
- **Fundamentals (60 pts)**: Valuation (16), Earnings Growth (14), Profit Margins (14), Debt Health (8), Institutional Ownership (4), Smart Money Flow (4).
- **Sentiment (15 pts)**: News sentiment (10 pts) + Finnhub insider MSPR (5 pts).
- **Projections (15 pts)**: Monte Carlo P50 upside (9 pts) + risk/reward ratio (6 pts).
- **Technicals (10 pts)**: SMA distance scoring (4), RSI optimal zone 50-65 (3), volume conviction (3).

**Sector Override Feature**:
- 29 industry-specific benchmarks (P/E median ranges 8-80 across sectors)
- Override dropdown in Recommendation Score header
- Options: Auto-detect, Standard, or specific sector (Cloud/SaaS, EV, Biotech, Banks, etc.)

**Outlooks (3m/6m/12m)**:
- **3 Months**: Technical/Momentum focus (RSI, SMA50, Sentiment, Beta)
- **6 Months**: Valuation/Growth focus (PEG, P/E, SMA200, Earnings Growth)
- **12 Months**: Quality/Fundamental focus (Margins, Debt, 52W Range, Dividends)

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
