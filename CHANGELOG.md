# Changelog

## [v9.8.0] - Institutional Portfolio Dashboard (2026-02-16)

### 📊 Portfolio Dashboard: Real-Time Intelligence
- **Dynamic Stats Bar**: Instant aggregate metrics for Net Worth, Total P&L ($, %), Day Change ($, %), and Total Cost basis.
- **Sector Allocation**: Integrated dynamic donut charts visualizing portfolio concentration across 12+ industry sectors.
    - *Refinement*: Optimized for high-density data with thin-crust design and percentage-based legends.
- **Enhanced Holdings Table**: A high-density, sortable interface for tracking asset performance, including live prices, quantity, and individual unrealized P&L.
- **Contextual UI**: The dashboard now intelligently swaps between the **AI Strategist** (Watchlists) and **AI Portfolio Manager** (Portfolios) based on user focus.

### 📥 Data Integration: Smooth Onboarding
- **Smart CSV Importer**: Built a robust parsing engine supporting generic (Symbol, Qty) and specific Robinhood Transaction exports.
- **Automated Enrichment**: Imported holdings are instantly hydrated with real-time market data and historical sector benchmarks.

### 🧠 AI Portfolio Manager
- **6-Point Institutional Audit**: DeepSeek R1-powered synthesis covering Health Score, Concentration Risk, Winner/Loser Analysis, Sector Audit, Risk Scenarios, and Actionable Recommendations.
- **Reliability Patch**: Resolved a critical 500 error in the AI summary pipeline caused by masked 404s on non-existent portfolios.

---


## [v9.7.1] - Strategist Transparency (2026-02-15)

### 🧠 AI Strategist
- **Extended Reasoning**: Increased backend timeout to **180s** to allow DeepSeek R1 to fully "think" without premature truncation.
- **Valuation Intelligence**: Injected **Forward P/E** and **PEG Ratio** into the prompt for deeper valuation analysis.
- **Model Transparency**: Added a "Model Used" badge (e.g., "DeepSeek R1" vs "Gemini 2.0") to the summary card footer.
- **UI Typography**: Refined Markdown headers and spacing for a cleaner, more institutional look.

## [v9.7.0] - Precision UI & Persona Logic (2026-02-15)

### 🧠 Backend: Engineered Consistency
- **Persona Weights**: Injected strict scoring rubrics for each persona (e.g., **Momentum**: 40% Technicals, **CFA**: 30% Valuation).
- **Zero-Temperature**: Lowered AI temperature to `0.1` (or `0.0`) across all providers (Groq, OpenRouter, DeepSeek, Gemini) to eliminate random variance.
- **Verdict Logic**: Enforced a strict "Rated X/100 because..." format for the verdict to ensure immediate clarity.
- **Consistency Rules**: Added hard caps for specific risks (e.g., "Max Score 60 if Debt/Equity > 2.0").

### 🎨 UI: Clarity & Polish
- **Verdict Placement**: Moved the full Verdict statement to the top Score Ring section for immediate visibility.
- **Rating Badge**: Added a dynamic **BUY / SELL / HOLD** badge next to the score.
- **Decluttered Header**: Removed redundant verdict text from the "AI Strategic Briefing" header.
- **Restored Lists**: Brought back "Key Opportunities" and "Key Risks" lists into the Bull/Bear cards for detailed context.

---

## [v9.6.0] - Speed & Strategy Architecture (2026-02-11)

### 🚀 Performance: Llama 3.3 Core
- **Instant Scoring**: Switched the primary scoring engine to **Llama 3.3 70B** (via Groq), reducing latency from ~45s (DeepSeek) to **<5s**.
- **Specialized Fallback**: DeepSeek R1 remains available as a high-precision fallback if speed is not the priority.

### 🧠 Major Upgrade: DeepSeek R1 Strategist
- **AI Strategist Integration**: The Watchlist Summary now uses **DeepSeek R1** (OpenRouter) as the primary engine.
- **Reasoning Depth**: Leverages R1's Chain-of-Thought (CoT) for institutional-grade portfolio synthesis.
- **UI Cleanliness**: Automated stripping of `<think>` tags ensures the summary card remains concise while benefiting from deep reasoning.

### 🛡️ Reliability Fixes
- **Institutional Data**: Fixed a critical `NoneType` crash in `finance.py` that occurred when Yahoo Finance returned incomplete stock info.
- **Groq Client Stability**: Resolved a regression where passing `timeout` to the Groq client caused 500 errors (parameter removed).
- **Adaptive Timeouts**: 
    - **Scoring**: 60s timeout (optimized for Llama 3.3).
    - **Strategist**: 120s timeout (accommodates DeepSeek R1 variance).

---
## [v9.5.0] - High-Performance Analytics & Conviction Index (2026-02-06)

### 🚀 Performance: Progressive Dashboard Architect
- **Zero-Block Rendering**: Re-engineered the Dashboard fetcher to prioritize fast market data and mathematical scores. 
- **AI Background Processing**: LLM reasoning now fetches in the background via a separate thread/hook, preventing slower AI providers from blocking the initial page load.
- **Micro-Skeletons**: Implemented granular loading states for individual AI components (Briefing, Sentiment) to maintain a responsive interactive feel.

### 📊 Major Feature: Institutional Conviction Index
- **Multi-Factor Synthesis**: Introduced a new "Conviction Index" card that mathematically blends:
    - **Algo Score (40%)**: Core fundamental/technical ground truth.
    - **Smart Money Signal (30%)**: Institutional and Insider movement strength.
    - **AI Sentiment (30%)**: Real-time news narrative pulse.
- **Dynamic Verdicts**: High-contrast progress bars and labels (Extreme / Strong / Moderate / Bearish) for instant trader decision-making.

### 🎨 UI & Search Enhancements
- **Global Health Bar**: Added a premium "Global Pulse" ticker at the top of the application for instant context on major indices (S&P 500, Nasdaq, BTC).
- **Search Context 2.0**: Watchlist search results now feature **Asset Class** (ETF/Index/Equity) and **Exchange** (NYSE/NASDAQ/etc.) badges.
- **Glassmorphism 2.0**: Enhanced backdrop-blur and translucent borders across all new analytics cards for a state-of-the-art terminal aesthetic.

### 🔧 Reliability & Fixes
- **Watchlist Stability**: Fixed several JSX edge cases in the search dropdown where large result lists would overlap action menus.
- **Real-time Polish**: Optimized sidebar price polling to ensure fluid movements and accurate performance percentages.

---

## [v9.4.0] - Institutional AI Strategist (2026-02-05)

### 🎨 UI: Premium AI Strategist Redesign
- **Intelligence Bar**: Re-engineered the "AI Strategist" header into a vibrant, high-contrast intelligence bar with glassmorphism effects.
- **Institutional Typography**: Implemented high-density, clean serif/sans-serif hybrid typography for the Briefing section.
- **Layout Tightening**: Removed decorative "bubbles" in favor of clean, bold text for tickers (Sky Blue) and performance metrics (Emerald/Rose).
- **Header Hierarchy**: Refined `h2` and `h3` headers with consistent casing, increased sizes (20px/15px), and optimized vertical rhythm.
- **Information Density**: Increased vertical breathing room while maintaining a "Bottom Line Up Front" (BLUF) data architecture.

### 🛡️ Reliability & Precision
- **Synchronized Intel**: Unified the "LIVE INTEL" status and timestamp with real-time portfolio updates.
- **Refresh UX**: Restored the vibrant solid-blue premium Refresh button with coordinated hover/spin animations.

---

## [v9.1.2] - Performance Architecture (2026-02-04)

### 🚀 Major Feature: Coordinated Data Fetching
- **One-Shot API**: Replaced "waterfall" API calls with a single `Coordinator` class that initializes a `yf.Ticker` object once and reuses it for News, Institutional, and Financials data.
- **Latency Reduction**: Dashboard analysis load times reduced by **~22%** (3.59s → 2.80s).
- **Rate Limit Safety**: Drastically reduced "Too Many Requests" errors from Yahoo Finance by cutting HTTP session overhead by 80%.

### ⚡ Watchlist Optimization
- **Batch History**: Re-engineered the Watchlist Sidebar to use `yf.download(tickers, period="1y")`.
- **Speed**: Fetches rich metrics (SMA, 5D%, YTD%) for 20+ stocks in a **single HTTP request** instead of 20 sequential requests.
- **Stability**: Eliminated "partial load" issues on the sidebar.

---

## [v9.1.1] - AI Reasoning vs. Algo Baseline Split (2026-02-04)

### 🚀 Major Feature: AI vs. Algorithmic Score Separation
- **Dual-Layer Analysis**: Separated the LLM's subjective conviction from the objective mathematical baseline.
- **AI Analyst Briefing**: The top section now displays scores derived independently by the AI Model (Llama 3.3/Gemini) based on 10-point component ratings.
- **Algorithmic Baseline**: The bottom "Score Breakdown" section serves as the "Ground Truth" using the v9.0 foundation (70% Fundamental / 30% Technical).
- **Visual Tagging**: High-visibility "v9.0 Foundation" tag and "Calculated Algo Score (70/30)" label added to the bottom section.

### 🛡️ Reliability: SMTP & API Key Governance
- **SMTP Fixed**: Confirmed functional mail delivery through authenticated Gmail SMTP.
- **Provider Support**: Added support for both `MAIL_` and `SMTP_` environment variable prefixes.
- **Key Validation**: Implemented `validate_keys.py` to health-check all integrated service keys (Groq, Gemini, Serper, Finnhub, EODHD).

### 🎨 UI Refinement
- **Tab Cleanup**: Removed duplicate Algorithmic Breakdown sections from the Sentiment tab.
- **Score Mapping**: Fixed a bug where both sections were pulling from the same data object, ensuring divergence is visible.
- **Executive Summary**: Repositioned AI Thesis next to the Score Ring for better UX.

---

## [v9.1.0] - Insider Intelligence & DIY Earnings (2026-02-03)

### 🚀 Major Feature: Insider "Cluster Selling" Detection
- **Heuristic Logic**: Backend now identifies **coordinated selling** patterns.
- **Cluster Definition**: 3+ unique executives selling within a **14-day sliding window**.
- **Visual Alert**:
    - 🔴 **Cluster Selling**: 3+ sells within 14 days (Score: -8, Red Badge).
    - 🟡 **Selling**: Net selling pressure without clustering (Score: -4, Yellow Badge).
    - 🟢 **Buying**: Net buying pressure (Score: +6, Green Badge).

### ⚡ Feature: DIY Earnings Scraper
- **Source Independence**: Removed dependency on paid "API Ninjas" for transcripts.
- **Search Engine**: Uses **Serper API** (primary) + DuckDuckGo (fallback) to find transcript URLs.
- **Scraper**: Custom `BeautifulSoup` engine extracts "Management Remarks" and "Q&A" from Motley Fool articles.
- **Perpetual Caching**: Scraped transcripts are saved in DB forever to minimize external requests.

### 🎨 UI Improvements
- **Clickable Logo**: "Vinsight" logo now redirects to Home (`/`).
- **Heading Update**: Earnings tab header renamed to **"Earnings Call AI"**.
- **Label Refinement**: Insider selling label now specifies "Sell by X insiders".

---

## [v9.0.1] - Senior Analyst Earnings AI (2026-02-02)

### 🚀 Major Feature: Institutional Earnings Intelligence
- **Senior Analyst Persona**: Re-engineered the earnings AI to act as a **Senior Wall Street Analyst (CFA)**. 
- **Strategy vs. Truth Split**: Transcripts are now analyzed in two distinct segments:
    - **Prepared Remarks**: Captures the CEO's scripted strategic narrative and growth pitch.
    - **Q&A Session**: Analyzes unscripted answers to identify hidden risks and analyst "revelations."
- **Retail-Ready Verdict**: Adds a decisive **Buy | Hold | Sell** rating and a one-sentence reasoning for instant retail investor clarity.

### 🎨 UI: Earnings Dashboard v2.0
- **Side-by-Side Analysis**: Redesigned the "Earnings" tab with a dual-card layout comparing management's pitch against historical Q&A data.
- **Verdict Header**: Added a high-visibility Analyst Verdict card with sentiment-aware color coding.

### 🔧 Backend & Performance
- **Groq Llama 3.3 Integration**: Migrated earnings analysis to Llama 3.3 (70B) on Groq for sub-2s processing times.
- **Structured JSON Schema**: Enforced a strict JSON output format for reliable UI rendering.
- **Precision Error Mapping**: Updated UI to distinguish between "No Data" and "Premium Access Required" (API Ninjas).
- **Rolled Back**: Removed Financial Modeling Prep (FMP) integration as their "Free" tier now blocks all transcript access (Legacy/Restricted). Reverted to API Ninjas logic (Premium-only).

---

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
- **Role-Based Handover**: Created a specialized **HANDOVER.md** guide for PM, Engineering, DevOps, and Business themes.
- **Legacy Cleanup**: Marked v7 and v8 logic docs as LEGACY to prevent cross-team confusion.
