# Changelog

## [v13.0.0] - Three-Axis Scoring Architecture & Backtesting (2026-03-26)

### 🚀 Major Feature: v13 Three-Axis Scoring Engine
- **Architecture Redesign**: Split the monolithic score into three independent axes — **Quality** (0-100), **Value** (0-100), and **Timing** (0-100) — with a persona-weighted **Conviction Score** combining all three.
- **Quality Axis**: ROE, margins, D/E, EPS stability, Altman Z, ROIC spread. No valuation metrics (clean separation from Value).
- **Value Axis (NEW)**: PEG, Forward P/E, FCF Yield, and **Residual Income Model (RIM)** margin of safety. Moved all valuation from Quality into this axis.
- **Timing Axis**: Price vs SMA50/200, RSI, relative volume, momentum signals.
- **Persona Conviction Weights**: Each persona applies different axis weights (e.g., CFA: Q=45%/V=30%/T=25%, Momentum: Q=10%/V=10%/T=80%).
- **Unified Entry Point**: `evaluate_v13()` in `vinsight_scorer.py` — backward-compatible `evaluate()` preserved.

### 🛡️ Guardian Thesis Integration
- **Conviction Modifiers**: `BROKEN` thesis → cap conviction at 40. `AT_RISK` → subtract 10pts.
- **One-Way Flow**: Guardian status fetched *before* scoring in `reasoning_scorer.py` to avoid circular dependencies.

### 📊 Backtesting Engine (Phase 3A)
- **New File**: `backend/services/backtest.py` — `Backtester` class with `run()`, `analyze()`, `generate_report_text()`.
- **Methodology**: Scores stocks at monthly historical snapshots using current fundamentals + reconstructed technicals (SMA50, SMA200, RSI, relative volume from historical prices).
- **Signal Validation**: 10-ticker × 12-month test (120 snapshots) — Elite tier (80-100) achieved **72% hit rate at 3mo**, **100% at 12mo**, **+7.4% excess return**. Avoid tier (0-49): 0% hit rate at 6/12mo, -17.6% excess.
- **Limitations**: Survivorship bias (only currently-listed stocks), point-in-time fundamentals.

### 🏗️ Data Provider Abstraction
- **New File**: `backend/services/data_provider.py` — `DataProvider` ABC with `YFinanceProvider` implementation.
- **Purpose**: Makes scoring engine data-source agnostic for future FMP/Bloomberg integration.

### 🎨 Three-Axis UI
- **Three Axis Cards**: Quality (emerald), Value (violet), Timing (blue) — each showing score, progress bar, and persona weight label.
- **Formula Transparency Bar**: `Conviction = Q(78)×45% + V(65)×30% + T(71)×25%` rendered inline.
- **Persona Lens Callout**: Purple badge showing why the selected persona rates the stock as it does.
- **Algo Breakdown**: Added **Valuation & Cheapness** as a third collapsible section between Quality and Timing.
- **Engine Label**: Updated from v12.0 to **v13.0**.

### 🧠 AI Pipeline Updates
- **Three-Axis Context**: LLM prompt now receives Quality, Value, Timing scores + weights for transparent narrative generation.
- **`persona_lens` Field**: New Pydantic field in `SummaryDetails` — LLM explains why the persona rates the stock at X/100.
- **v13 as Authority**: `reasoning_scorer.py` uses `v13_result` as the authoritative score source.

---

## [v12.0.0] - The v12 Engine & Dynamic Optimization (2026-03-23)

### 🚀 Major Feature: The v12 Engine (v12.0)
- **Advanced Reasoning Architecture**: Fully integrated the ReasoningScorer as the primary intelligence layer, replacing pure mathematical formulas with hybrid AI-driven synthesis.
- **Deep-Thinking Capabilities**: Leverages DeepSeek R1 and Llama 3.3 70B for institutional-grade bull/bear cases and goal-aligned investment verdicts.
- **V12 Performance Layer**: Optimized the "Analysis" pipeline to handle 180s reasoning windows, ensuring deep CoT (Chain of Thought) is not truncated.
- **Goal Alignment**: The AI now incorporates User Profiles (risk appetite, time horizon, specific goals) directly into its scoring logic via a new `contextual_adjustment` layer (±10 points).

### 🛠️ Stability & Resilience
- **Zero-Stall UI**: Added "AI is reasoning..." narrative placeholders to the initial data load, eliminating the "Analyzing..." flicker and ensuring a smooth user experience.
- **Adaptive Timeouts**: Increased frontend analyzer timeout to **180,000ms (3 minutes)** and implemented strict internal provider timeouts (30s Anthropic / 15s Groq) to ensure rapid failover.
- **Null-Safety Guardrails**: Patched `finance.py` coordinated fetcher and institutional parser to handle missing or null API fields, eliminating `NoneType` crashes for stocks with partial data (e.g., AAPL).
- **Backend Sync**: Synchronized all internal metadata and metadata-headers to `v12.0`.

### 🎨 UI & UX
- **Refined AI Strategist**: Extracted the "Algorithmic Score Breakdown" into a reusable component, making it available in both the AI tab and the Fundamentals tab.
- **Unified Versioning**: Standardized "v12.0 Engine" branding across the dashboard and reasoning badges.

---


## [v11.3.0] - AI Thesis Library & Guardian Sync (2026-03-06)

### 🚀 Major Feature: The AI Thesis Library
- **Unified Navigation**: Extracted Watchlists, Portfolios, and Thesis Library to top-level navigation tabs.
- **Master-Detail UI**: Built a dedicated Thesis Library interface (`ThesisList` and `ThesisDetail`) for managing AI-generated investment theses.
- **Deep Generation API**: Upgraded `/api/theses/generate` to use the full AI model, generating Stance (BULLISH/BEARISH/NEUTRAL), One-Liners, Key Drivers, Risks, Confidence Scores, and Deep Dives.
- **Interactive Management**: Added functionality to seamlessly Regenerate, Edit, and Delete theses directly from the UI.

### 🛡️ Guardian Agent Integration
- **Bidirectional Syncing**: Activating the Thesis Agent for a stock automatically populates the Thesis Library. Deleting a thesis correctly disables the background Guardian monitoring.
- **Manual "Scan Now" Overrides**: Added `/api/guardian/scan/{symbol}`. Users can trigger an on-demand, rigorous Guardian evaluation of a thesis (rate-limited to 1 per day per stock).
- **Incident Log Hub**: Integrated the Guardian status (INTACT / AT_RISK / BROKEN) and historical stress-test Incident Logs natively into the Thesis Detail view.

### ⚙️ Backend & Resilience 
- **LLM JSON Parsing Reliability**: Enforced strict escaping rules (`\"`, `\n`) in the AI prompt and implemented `strict=False` in Python's JSON parser to prevent crashes caused by unescaped characters in AI-generated markdown.
- **Event Loop Management**: Offloaded synchronous LLM generation calls inside the FastAPI `/scan` route entirely to background worker threads. This eliminated a critical bug where long AI reasoning times would freeze the main web server and trigger 500 errors across the application.
- **Compact UI Enhancements**: Replaced massive Guardian headers with sleek, space-efficient single-row badges. Replaced browser alerts with elegantly styled inline Toast notifications.

---

## [v11.2.0] - On-Demand Pure Text SEC RAG (2026-03-06)

### 🚀 Major Feature: Thesis Agent Text RAG
- **Zero-Cost Ingestion**: Built a new `sec_summarizer.py` microservice that dynamically checks SEC metadata for new 10-K/10-Q filing dates before scraping.
- **Pure Text Caching**: Ripped out computationally heavy `pgvector`/FAISS vector embeddings. We now pre-summarize SEC 10-K risk factors and MD&A via `Gemini 2.0 Flash` (to leverage its massive 1M token context window) and store them in local SQLite (`finance.db`) as highly dense pure text blocks.
- **Prompt Injection**: The `guardian_agent.py` no longer "guesses" vector search queries. It explicitly injects the pre-calculated SEC Risk Summary straight into the DeepSeek/Gemini baseline context window for 100% accurate recall.
- **Tech Debt Cleanup**: Deleted all legacy vector FAISS indexing scripts, `sec_rag.py`, and multi-gigabyte `.pkl`/`.faiss` storage folders to streamline Cloud Run deployments.

---

## [v10.0.0] - The Era of Objectivity (2026-02-19)

### 🚀 Scoring Engine: VinSight v10.0
- **10-Tier Rubric**: Replaced binary Buy/Sell with a calibrated decile system (`0-19` Bankruptcy to `90-100` Generational).
- **Universal Kill Switches**: Explicit point deductions for "Solvency Risk" (-20pts), "Valuation Cap" (-15pts), and "Momentum Crash" (-10pts).
- **Confidence Weighting**: AI confidence score now mathematically discounts the final rating (e.g., 50% confidence = 50% score reduction).

### 🎨 UI Transparency
- **Penalty Badges**: Red/Amber tags visible below the score ring showing active kill switches.
- **Confidence Meter**: Visual bar indicating AI's certainty level.
- **Assessment Tooltip**: New `ⓘ` icon explaining the active persona's scoring logic.

### 🧠 Backend
- **Persona Tuning**: Calibrated prompt sensitivity for `Value`, `Growth`, `Momentum`, and `CFA` personas.
- **Math Engine**: Aligned `vinsight_scorer` fallback model with the new 10-tier mapping.

---

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
- **Added Agentic Portfolio Guardian** with deep-thinking reasoning loop.
- Integrated `edgartools` for robust SEC 10-K parsing.
- Implemented Guardian Guardrails: Evidence Grounding, Reasoning Caps, and Rate Limiting.
- **6-Point Institutional Audit**: DeepSeek R1-powered synthesis covering Health Score, Concentration Risk, Winner/Loser Analysis, Sector Audit, Risk Scenarios, and Actionable Recommendations.
- **Reliability Patch**: Resolved a critical 500 error in the AI summary pipeline caused by masked 404s on non-existent portfolios.
- Planned Phase 5 migration to `pgvector` on Cloud SQL for production vector storage.

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
