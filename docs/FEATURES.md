# Features of VinSight

## 1. Real-Time Dashboard
- **Candlestick Chart**: Custom-built using `lightweight-charts`. Shows Open, High, Low, Close data.
- **Volume Bars**: Visual representation of trading activity.
- **Timeframes**: Switch between Daily, Weekly, and Intraday views.

## 2. Artificial Intelligence
- **Sentiment Analysis**:
    - We fetch the latest news using Google News RSS.
    - **Groq (Llama 3)** analyzes headlines for immediate sentiment (Positive/Negative/Neutral).
    - **Gemini 1.5 Pro** performs "Deep Reasoning" on earnings reports to find hidden risks.
- **AI Analyst**: An automated agent that summarizes the financial health of a company in natural language.

## 3. VinSight Score
A proprietary algorithm that combines:
- Technical Indicators (RSI, MACD)
- Fundamental Data (P/E Ratio, EPS)
- Sentiment Score (AI derived)
**Result**: A single score from 0-100 indicating stock health.

## 4. Smart Alerts
- **Price Alerts**: "Tell me if AAPL goes above $200".
- **Sentiment Alerts**: "Warn me if news turns negative".
- **Delivery**: Alerts are sent via Email (SMTP).

## 5. Security
- **JWT Authentication**: Secure login system.
- **Password Hashing**: PBKDF2 hashing for user passwords.
- **Role Based Access**: (Planned for v2).
