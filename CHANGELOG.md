# Changelog

## [v9.0.0] - Dynamic Benchmarking & Unified UI (2026-02-02)

### 🚀 Major Feature: Adaptive Sector Benchmarking
- **Engine v9.0**: Transitioned from rigid metric targets to **Dynamic Sector Thresholds**.
- **Contextual Pricing**: PEG, FCF Yield, ROE, and Margin targets are now fetched from industry-specific benchmarks (e.g., Tech vs. Energy have different "ideal" values).
- **Linear Interpolation 2.0**: Scoring curves automatically map "Poor" to "Excellent" based on the sector's unique financial architecture.

### 🎨 UI: Professional Consolidation
- **Unified Strategy Mixer**: Merged the strategy title, weighting stats, and slider into a single, compact, bio-metric-style header.
- **Sentiment Consolidation**: Merged "Today's Pulse" and "Weekly Trend" cards into a single high-density sentiment block, reducing vertical height by 40%.
- **Mobile-First Refinement**: Drastically reduced vertical footprint across the dashboard.
- **Deep Collapsibles**: Detailed score breakdown tables are now individually collapsible and closed by default for a cleaner "Bottom Line Up Front" experience.
- **Vibrant Modifiers**: Modifiers/Vetos now use high-contrast Red/Green color coding and human-readable text (removed technical "VETO:" prefixes).

### 🧠 Logic & Intelligence
- **Strategy Labeling**: Added automatic strategy categorization based on weights: **Value Purist**, **Fundamental**, **Balanced**, and **Trader**.
- **CFA Engine v5.0**: Refined the core composite engine to better handle mid-cycle sector rotations through the dynamic benchmark layer.

### 📚 Project Sustainability & Handover
- **Comprehensive Documentation**: Updated **README**, **ARCHITECTURE**, **FEATURES**, and **SETUP** guides for v9.0 alignment.
- **Dynamic Logic Guide**: Created [VINSIGHT_SCORER_V9_DYNAMIC_LOGIC.md](docs/VINSIGHT_SCORER_V9_DYNAMIC_LOGIC.md) for institutional logic transparency.
- **Role-Based Handover**: Created a specialized **HANDOVER.md** guide for PM, Engineering, DevOps, and Business teams.
- **Legacy Cleanup**: Marked v7 and v8 logic docs as LEGACY to prevent cross-team confusion.

---

## [v8.0.0] - CFA Scoring Engine & Senior Analyst AI (2026-02-02)

### 🚀 Major Feature: CFA-Level Scoring Engine
- **Weighted Composite Model**: Transitioned to a **70% Quality / 30% Timing** split, adhering to CFA institute principles of fundamental analysis.
- **Quality Score (70 pts)**:
    - **Valuation (35%)**: PEG Ratio (<1.0 ideal), FCF Yield (>5%).
    - **Profitability (35%)**: ROE (>20%), Net Margins (>20%), Gross Margin Trend (Rising).
    - **Health (20%)**: Debt/EBITDA (<3.0x), Altman Z-Score (>3.0 Safe Zone).
    - **Growth (10%)**: 3-Year Revenue CAGR (>15%).
- **Timing Score (30 pts)**:
    - **Trend (50%)**: Price vs SMA200 & SMA50.
    - **Momentum (15%)**: RSI (Bullish Zone 40-65).
    - **Volume (15%)**: Relative Volume (>1.5x breakout).
    - **Risk (20%)**: Beta (<1.2) and Distance to High (<15%).

### 🛡️ Kill Switches (Vetos)
- **Insolvency Veto**: If `Interest Coverage < 1.5x`, Total Score is capped at 40 (Sell).
- **Valuation Veto**: If `PEG > 4.0`, Quality Score is capped at 50.
- **Downtrend Veto**: If Price < SMA200 & SMA50, Timing Score is capped at 30.

### 🧠 Senior Equity Analyst AI
- **New Persona**: "Cynical CFA Analyst". Decisive, data-driven, and jargon-heavy.
- **Structured Output**: AI now returns a JSON object with:
    - **Executive Summary**: 2-sentence thesis.
    - **Factor Analysis**: Specific comments on Quality vs Timing.
    - **Risk Factors**: Bulleted list of primary risks.
    - **Strategic Outlook**: 3m (Tactical), 6m (Catalyst), 12m (Strategic) horizons.

### 📊 UI Updates
- **Split Scoring**: Dashboard now displays separate "Quality" and "Timing" sub-scores.
- **AI Briefing Card**: Magazine-style layout for the AI's "Executive Summary", with distinct sections for Thesis, Risks, and Outlooks.

---
### 🧠 AI Analyst "Expert Mode"
- **Actionable Outlooks**: AI prompt heavily refined to produce specific, catalyst-driven insights (e.g., "Bullish flag break", "Undervalued ahead of earnings").
- **Concise Thesis**: "Bottom Line Up Front" logic applied.
- **Score Explanation**: Dynamic "Why" header added to the recommendation card (e.g., "Fundamentals strong but suppressed by negative trend").

### 🎨 UI Overhaul (Recommendation Tab)
- **Header Redesign**: Removed static labels, moved Score Ring + Context to a unified top bar.
- **Magazine-Style Grid**: Full-width layout for AI briefing with distinct Left-Accent color coding.
- **RSI Visibility**: Explicit "RSI Safety" row (Bonus/Penalty) added to the Detailed Breakdown table.
- **RSI Badges**: Blue (Oversold) and Red (Overbought) badges now visually distinct.

### 🔧 Scoring Tweaks
- **Trend Gate**: Penalty reduced from -15 to **-10** (less punitive for counter-trend value plays).

---

## [v7.4] - 2026-02-01
### Added
- **10-Theme Benchmarking**: Consolidated 30+ sectors into 10 broad strategies (High Growth Tech, Mature Tech, etc.).
- **Market Reference**: Added S&P 500 columns to Scorer output for broad market context.
- **Risk Gates**: Formalized penalties for Technical Downtrends (-15 pts) and Monte Carlo Risk (-15 pts).
- **Optimization**: Disabled Deep Sentiment analysis for faster scorer loading.

## [v7.0 - v7.3] - 2026-02-01
- **Fundamental Purist Refactor**: Scorer is now 100% Fundamentals.
- **New Metrics**: ROE, ROA, Forward PE, Operating Margins.

 

## v6.7.2 - Insider & Institutional Refinement (2026-02-01)

### 🏛️ Institutional Holdings (Smart Money)
- **Unified Card**: Merged "Smart Money" signal, Net Change, and QoQ Reporting Period into a single, high-level summary card.
- **Reporting Period**: Added dynamic detection of the latest reporting quarter (e.g., "Q4 2025 Filings").

### 💼 Insider Activity (90-Day Discretionary)
- **Heuristic Filtering (10b5-1)**: Backend now automatically distinguishes "Automatic" (Plan/Grant) trades from "Real" (Discretionary) trades based on SEC text patterns.
- **Signal Logic**: Score and Label are now calculated exclusively on **Discretionary** trades to capture true executive sentiment.
- **3-Level Hierarchy UI**:
    - **Level 1**: Glanceable Badge with One-Liner Context (e.g., "Cluster of 3 executives selling").
    - **Level 2**: Metrics showing Net Flow, Trade Volume, and "Real vs Auto" Count.
    - **Level 3**: Expandable Transaction Table (Top 10 default) with explicit "Type" column.

---
## v6.7.1 - MSPR Refactor to Display-Only (2026-02-01)

### 🔧 Scoring Engine (v6.5)
- **Insider Scoring Removed**: Removed `insider_activity` from VinSight scoring. Sentiment pillar now awards full 10 points based on news sentiment only.

### 📊 Sentiment Tab Enhancement
- **New MSPR Section**: Added "Insider Sentiment (MSPR)" card with source info (Finnhub API, SEC Form 4 filings, 3-month window).

---

## v6.7.0 - Enhanced Projections & AI Sentiment (2026-02-01)

### 🚀 New Projections Tab Features
- **Monte Carlo Engine Enhancements**: 
    - Added Probability Analysis table (+25%/+10%/Break-even/-10%/-25% gain/loss probabilities)
    - Added Return Distribution Histogram with interactive chart
    - Added Volatility calculation (annualized %)
- **Analyst Consensus Integration**: Fetches and displays Yahoo Finance analyst price targets (target_low, target_mean, target_high) and recommendations
- **Risk Metrics Row**: Four key metrics displayed prominently (Expected Return, VaR 95%, Prob. of Loss, Volatility)
- **Scenario Cards with Percentile Labels**: Bear Case (P10), Base Case (P50), Bull Case (P90) with clear labeling
- **UI Cleanup**: Removed Monte Carlo line chart, merged redundant sections, moved scenarios to top for immediate visibility
- **Duration Selector**: Added 90-day duration indicator with rerun button

### 🔧 AI Sentiment Tab
- **Renamed**: "Sentiment" → "AI Sentiment" for clarity
- **On-Demand Loading**: Analysis triggers automatically when the tab is clicked

### 🐛 Fixes
- Fixed redundant P10/P50/P90 display (removed duplicate section)
- Improved card layout and percentile indicator visibility

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
