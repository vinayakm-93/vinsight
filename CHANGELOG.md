# Changelog
 


## v6.6.1 - Dashboard Refactor & Finnhub News (2026-01-31)

### 🚀 UI & UX Overhaul
- **Dedicated Projections Tab**: Moved Monte Carlo Simulation to a new top-level tab, removing the dashboard summary card to reduce clutter.
- **On-Demand Simulation**: Simulation now only runs when the "Projections" tab is active, significantly improving initial dashboard load time. Includes P10/P50/P90 visualization.
- **News Feed Relocation**: Moved "Global News & Recent Events" to the bottom of the dashboard for a full-width reading experience.
- **Scorecard Removal**: Removed the rigid Fundamentals/Sentiment/Technicals grid in favor of a cleaner tab-based layout.

### 🔌 Integrations
- **Finnhub News API**: Replaced legacy news sources with Finnhub's Limited News API for more reliable, real-time market news.
- **Sentiment Auto-Refresh**: The "Sentiment" tab now automatically refreshes its analysis upon clicking, ensuring the latest data is used.

### 🐛 Fixes
- **Simulation Graph**: Fixed an issue where the simulation chart height would collapse to 0, making the graph invisible.
- **Deployment**: Fixed missing `FINNHUB_API_KEY` injection in Cloud Run deployment script.

## v6.6.0 - UI Optimization & Dynamic Scoring (2026-01-23)

### 🚀 UI Improvements
- **Collapsible Detail Sections**: "Detailed Score Breakdown" and "Outlooks" are now collapsible (closed by default) to declutter the interface.
- **Consistent Typography**: Reduced header fonts (`text-sm`) and score fonts (`text-base`) to improve alignment and hierarchy in the Pillar cards.
- **Visual Spacing**: Added consistent `gap-4` spacing between Pillar Headers and Scores to prevent crowding on smaller screens.
- **Refined Outlooks**: Outlook cards now display actionable sub-metrics (e.g., "RSI is oversold", "VinSight Rating: Buy") for quicker decision-making.

### 🔧 Scoring Engine Refactor
- **Dynamic Sector Benchmarks**: Refactored `vinsight_scorer.py` to use dynamic benchmarks from configuration instead of hardcoded values.
- **New Benchmarks Added**: Added `fcf_yield_strong` (5%) and `eps_surprise_huge` (10%) to `sector_benchmarks.json`.
- **Score Consistency**: Guaranteed that the "Score Explanation" text (e.g., "Margins > 12%") matches the actual scoring logic threshold.

### 🧪 Validation
- **Unit Tests**: Full coverage for new scoring weights and components (`test_vinsight_scorer_unit.py`).
- **Browser Verification**: Validated interactive dropdowns and responsive layout.

## v6.5.0 - Watchlist & Dashboard Optimization (2026-01-23)

### 🚀 Performance
- **Watchlist Sidebar**: Created dedicated lightweight endpoint (`/api/data/batch-prices`) using `fast_info`.
- **Latency Reduction**: Batch price fetching reduced from ~500ms+ (variable) to **~30ms per ticker** overhead, ensuring sub-1.5s loads for large watchlists.
- **Efficient Data**: Eliminated over-fetching of historical data for simple sidebar price updates.

### 📈 Features
- **Dashboard YTD%**: Added Year-to-Date (YTD) percentage column to the Watchlist Overview table in the Dashboard.
- **Backend Calc**: Implemented robust YTD calculation using existing 1-year history data without extra API calls.

---

## v6.4.0 - Page Speed Optimization (2026-01-23)

### 🚀 Performance
- **Monte Carlo Vectorization**: Replaced Python loops with NumPy vector operations, reducing simulation time from **0.40s to 0.02s** (20x speedup).
- **API Unification**: Consolidated `Analysis`, `History`, `News`, `Institutional`, and `Basic Info` into a single API call (`/api/data/analysis`), reducing network round trips.
- **Frontend Optimization**: Dashboard component now loads all critical data in a single initial request, preventing layout shift and "pop-in" effects.
- **Total Latency**: Single Stock Page load time reduced by **~60%** (1.92s → 0.76s).

---

## v6.3.0 - Single Stock Optimization & Reliability (2026-01-23)

### 🚀 Performance Improvements
- **Parallel Data Fetching**: Refactored `get_technical_analysis` to fetch History, Stock Info, News, and Institutional data concurrently using `ThreadPoolExecutor`.
- **API Consolidation**: Merged `simulation`, `institutional`, and `news` data into the single `/analysis` endpoint response.
- **Load Time Reduction**: Reduced Single Stock Page load time from **~2.6s to ~1.2s (55% faster)**.
- **CPU Optimization**: Eliminated redundant Monte Carlo simulations by sharing calculation results between analysis and frontend state.

### 🛡️ Reliability & Fixes
- **Graceful Degradation**: Implemented catch-all blocks for individual API calls (News, History). Partial failures (e.g., News API down) no longer crash the entire dashboard.
- **Production Fix**: Downgraded `uvicorn` to `0.30.6` to resolve `AttributeError: '_TrustedHosts' object has no attribute '_version'` caused by proxy headers middleware incompatibility in newer versions.
- **Watchlist Optimization**: Implemented batch fetching for watchlist prices to reduce rate limiting issues.

---

## v6.2.2 - Stability & Alerts Fix (2026-01-22)

### 🐛 Critical Bug Fixes
- **Validation Fix**: Resolved `NaN` crash in `backend/main.py`.
- **Infrastructure Fix**: Increased backend memory limit to 2Gi to handle `torch`/ML dependencies (Fixed OOM crash).
- **Routing Fix**: Updated `backend/routes/alerts.py` to allow paths without trailing slashes (Fixed `404 Not Found`).
- **Use Experience**: Added detailed backend error mapping (422/500/401) to frontend toast notifications.

### ⚡ Improvements
- **Auto-Queue Removal**: Triggered alerts are now automatically deleted from definition, keeping the user's list clean.

---

## v6.2.1 - Alert System Hotfix (2026-01-22)

### 🐛 Bug Fixes
- **Alert Creation Failure**: Fixed `ValueError` caused by `NaN` values in financial data by implementing a custom `NaNJSONResponse` using `simplejson` to safely handle invalid float values.
- **Logging**: Added verification logging for alert payloads and enhanced frontend error reporting to browser console.

---

## v6.2.0 - Theme Engine & Localhost Fixes (2026-01-22)

### 🚀 Improvements

#### Theme Toggle Logic (Tailwind v4)
- Fixed theme toggle (Light/Dark/System) by adding explicit `@variant dark` support in `globals.css`.
- Enabled manual theme overrides to work independently of system preferences.
- Ensured `dark:` utility classes respond correctly to the `.dark` class on `<html>`.

### 🐛 Bug Fixes
- Restored `localhost` accessibility by restarting backend (FastAPI/Uvicorn) and frontend (Next.js) development servers.
- Fixed issue where Tailwind `dark:` prefixed classes were ignored in Dark Mode.

---

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
