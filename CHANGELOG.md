# Changelog

## v6.1.0 - Sector Expansion & Weight Rebalance (2025-12-17)

### 🚀 New Features

#### Expanded Sector Benchmarks (29 total)
- Added 14 new sub-industries with distinct thresholds:
  - **Tech**: Cloud/SaaS, Fintech, Cybersecurity, AI/ML, Gaming
  - **Media**: Streaming/Media, E-commerce
  - **Specialty**: EV/Clean Energy, Biotech, Pharma
  - **Financial**: Banks, Insurance, REITs
  - **Industrial**: Aerospace & Defense, Mining, Luxury Goods
- Widened variance: P/E median ranges 8 (Mining) → 80 (EV/Clean Energy)

#### Sector Override Dropdown Moved
- Dropdown relocated from Fundamentals pillar to Recommendation Score header
- Shows all 31 options (29 sectors + Auto + Standard)

### 🔧 Scoring Rebalance (v6.1)
- **Fundamentals**: 55 → **60 pts** (Valuation 16, Growth 14, Margins 14, Debt 8, Inst 4, Flow 4)
- **Sentiment**: 15 pts (unchanged)
- **Projections**: 15 pts (unchanged)
- **Technicals**: 15 → **10 pts** (Trend 4, RSI 3, Volume 3)

#### UI Pillar Order Updated
Now displays: **Fundamentals → Sentiment → Projections → Technicals**

### 📊 Outlook Refactor (3m/6m/12m)
- **3 Months**: Technical/Momentum (RSI, SMA50, Sentiment, Beta)
- **6 Months**: Valuation/Growth (PEG, P/E, SMA200, Earnings Growth)
- **12 Months**: Quality/Fundamentals (Margins, Debt, 52W Range, Dividends, Market Cap)

### 🐛 Bug Fixes
- Fixed `sector` variable bug in `data.py:441` (was using undefined `sector` instead of `active_sector`)
- Monte Carlo tooltip: cleaner UI, day indicator, hides individual path noise

---

## v6.0.0 - Industry Peer Values UI (2025-12-17)

### 🚀 New Features

#### Industry Peer Values Display
- Added compact "Industry Peers" section at bottom of Fundamentals pillar expansion
- Shows sector-specific benchmarks: PEG Fair, Growth %, Margin %, Debt ratio
- New API endpoint: `/api/data/sector-benchmarks`

### 🔧 Scoring Rebalance (Retail Investor Focus)
- **Fundamentals**: 30 → 55 pts (more weight on company health)
- **Technicals**: 30 → 15 pts
- **Sentiment**: 20 → 15 pts
- **Projections**: 20 → 15 pts

New sub-factors: Profit Margins (10 pts), Debt Health (8 pts)

---

## v5.1.0 - Range-Based Scoring & Finnhub (2025-12-17)

### 🚀 New Features

#### Finnhub Insider Sentiment Integration
- Added `finnhub_insider.py` - MSPR (Monthly Share Purchase Ratio) analysis
- Uses SEC Form 3/4/5 data for accurate insider sentiment
- MSPR thresholds: >20 = Buying, -20-20 = Neutral, <-50 = Heavy Selling
- 15-minute caching to respect rate limits (60 calls/min free tier)

#### Range-Based Scoring (No Binary Yes/No)
- **All 4 pillars** now use linear interpolation for partial credits
- Sector-specific benchmarks for peer comparison
- Institutional ownership level now scored (7 pts)

### 🔧 Improvements

#### Fundamentals (30 pts)
- **Valuation**: PEG 1.0→8pts, fair→4pts, 3.0→0pts (interpolated)
- **Earnings**: Sector-adjusted thresholds (Tech 15%, Financial 8%)
- **Inst Ownership**: 80%+→7pts, 60%→5pts (NEW)
- **Smart Money**: Rising→7, Flat→4, Falling→1

#### Technicals (30 pts)
- **Trend**: Distance from SMAs (not just above/below)
- **RSI**: Optimal zone 50-65, smooth interpolation
- **Volume**: Weak/Mixed gets 5pts (not 0)

#### Sentiment (20 pts / was 10+10)
- **News**: 12 pts with score interpolation
- **Insider**: 8 pts with Finnhub MSPR

#### Projections (20 pts)
- **Upside**: 0%→3, 5%→6, 10%→9, 15%→12 pts
- **Risk/Reward**: 3x→8, 2x→6, 1x→2 pts

### 🐛 Bug Fixes
- Fixed momentum detection (now Bullish when price > SMA50)
- Fixed insider "Heavy Selling" false positives (stock gifts excluded)
- Communication Services P/E median: 18 → 25

### ⚙️ Configuration
New environment variable:
```
FINNHUB_API_KEY=  # Optional, get free from finnhub.io
```

---

## v2.5.0 - AI Score Improvements (2025-12-17)

### 🚀 New Features

#### Alpha Vantage News Integration
- 15-minute caching to respect rate limits
- Graceful fallback to Groq → TextBlob

#### Enhanced Sentiment Analysis
- Hybrid approach: Alpha Vantage → Groq → TextBlob fallback chain
- Removed redundant bullish keywords (LLM handles this)
- Kept bearish keywords for spin detection safety

### 🔧 Improvements

#### Industry-Standard Benchmarks
- **RSI Thresholds**: Changed from 40/80 to industry-standard 30/70
- **P/E Valuation**: Added Graham threshold (P/E < 15 = value)
- **PEG Ratio**: Peter Lynch thresholds (< 1.0 undervalued)
- **Earnings Growth**: Sector-specific thresholds (Tech needs >15%, Banks >8%)

#### Technical Scoring
- Added oversold turnaround bonus (+3 pts if RSI < 30)
- Added "Price Falling + Vol Rising" scoring
- RSI 50-65 with volume now scores 8 pts (healthy range)

#### Outlook Logic
- Added beta risk assessment for short-term signals
- Added 52-week range positioning
- Added STRONG BUY (score≥4) and WEAK HOLD ratings
- Enhanced signals with emoji indicators

### 🐛 Bug Fixes
- **Cluster Selling**: Now correctly scores 10 (not 0) for positive news + cluster selling
- **No Activity**: Added as valid insider activity type (10 pts)
- Fixed duplicate exception handlers in analysis.py

### 📦 Dependencies
- No new dependencies required

### ⚙️ Configuration
New environment variable:
```
ALPHA_VANTAGE_API_KEY=  # Optional, get free from alphavantage.co
```
