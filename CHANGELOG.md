# Changelog

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
