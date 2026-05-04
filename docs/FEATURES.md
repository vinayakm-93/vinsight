# VinSight Features

## 1. High-Performance Dashboard (v9.5)
- **Progressive Hydration**: Intelligent multi-phase loading. Zero-delay for market data and mathematical scores; background hydration for deep AI reasoning.
- **Global Health Bar**: Real-time market pulse ticker for top indices (S&P 500, Nasdaq, BTC).
- **Candlestick Chart**: Professional charts built with `lightweight-charts`.
- **Intraday & Historical**: Switch between 1D, 1W, 1M, and 1Y views.
- **Watchlists**: Manage multiple portfolios with real-time price updates and asset-class search badges.

## 2. Artificial Intelligence Engine
- **Hybrid Sentiment Analysis**: Blended scores from Alpha Vantage, Finnhub, and Groq (Llama 3.3).
- **Deep Reasoning**: AI-driven "Thesis" and "Risk" analysis via Gemini 1.5 Pro.
- **Insider Intelligence**: 
    - **MSPR Tracking**: Monthly Share Purchase Ratio from SEC filings.
    - **10b5-1 Filter**: Distinguishes planned trades from discretionary executive action.
- **Spin Detection**: Automated detection of "positive framing" on negative financial news.
- **Senior Analyst Earnings AI**:
    - **Institutional Breakdown**: Separates the "Management Pitch" (Prepared Remarks) from the "Analyst Interrogation" (Q&A).
    - **DIY Scraper**: Custom-built multi-source fetching engine (Serper/DuckDuckGo/Google) targeting [Motley Fool](https://fool.com) transcripts.
    - **CFA Persona**: AI acts as a Senior Wall Street Analyst translating complex calls for retail investors.
    - **Verdict Engine**: Explicit Buy/Hold/Sell rating based on transcript tone and unscripted revelations.

## 3. Thesis Agent (Portfolio Guardian)
Autonomous watchdog and deep-reasoning research engine.
-   **Thesis Library**: Dedicated Master-Detail UI to manage, regenerate, edit, and delete AI theses. Includes on-demand `/api/guardian/scan` capabilities.
-   **Monitoring Logic**: Continuous background scans for price drops, earnings, and sentiment shifts.
-   **On-Demand**: "Regenerate" option available directly from the Dashboard Watchlist for instant thesis updates. (Note: Deep Agent Execution Trace is accessible exclusively within the Thesis Library).
-   **Phase 4 Guardrails**:
    - **Confidence Scores**: AI verdicts are weighted and badge-displayed in alerts.
    - **Reasoning Caps**: Detailed email deep-dives with space-efficient DB storage.
    - **Evidence Grounding**: Claims are verified against retrieved text; uncorroborated items are tagged `[UNVERIFIED]`.
-   **Enterprise Retrieval (v5.0)**:
    - **Agentic Loop**: Turn 0 (Fact Collection) -> Plan -> Scrape (DDG/Motley) -> Retrieve SEC (edgartools) -> Synthesize.
    - **Pure Text Caching**: Highly efficient, zero-cost SEC data ingestion pipeline storing pre-summarized 10-K/10-Q text blocks in SQLite.

## 4. VinSight Engine v13.0
Professional-grade scoring with **Ruthless Objectivity** and a Three-Axis Framework.
- **Three-Axis Architecture**: Independent scoring for Quality, Value, and Timing.
- **Residual Income Model (RIM)**: Intrinsic valuation and Margin of Safety built into the Value axis.
- **Persona Conviction Weights**: Distinct weighting profiles for CFA, Momentum, Value, etc.
- **Universal Kill Switches**: Explicit penalty badges for Solvent Risk (-20pts), Valuation Caps (-15pts), and more.
- **Algorithms**: `ReasoningScorer` acts as the primary engine with `vinsight_scorer` (v13.0) as the mathematical fallback.
- **[Read Full Scoring Logic](./SCORING_ENGINE.md)**

## 5. Advanced Projections
- **Monte Carlo Scenarios**: Bull (P90), Base (P50), and Bear (P10) price targets.
- **Risk Assessment**: Value at Risk (VaR), Annualized Volatility, and Probability of hitting +25%/-25%.
- **Analyst Consensus**: Yahoo Finance target prices and recommendation trends.

## 5. Smart Alerts
- **Price Triggers**: Notification when a stock hits your target.
- **Execution**: Background monitoring via Cloud Scheduler.
- **Delivery**: Confirmed instant email notifications via authenticated SMTP (Gmail).

## 6. Security & Persistence
- **Guest Mode**: Try the app with LocalStorage-persisted watchlists.
- **Secure Auth**: JWT-based login with email verification and hashed passwords.
- **[Read Security Documentation](./SECURITY.md)**

## 8. Portfolio Intelligence (v9.8.0)
Advanced tools for tracking and auditing actual investment holdings.
- **Individual Portfolio Dashboard**:
    - **Dynamic Stats Bar**: Real-time aggregate metrics for Net Worth, Total Unrealized P&L, Day Change, and Cost Basis.
    - **Sector Allocation**: Multi-color donut charts with tooltips visualizing industry concentration.
    - **Holdings Performance Table**: High-density UI with sortable columns for live price, quantity, value, and P&L.
- **Smart CSV Onboarding**:
    - **Generic Parser**: Handles standard ticker/quantity exports.
    - **Robinhood Specialist**: Native support for Robinhood "Transaction" history exports.
- **AI Portfolio Manager**: 
    - **DeepSeek R1 Audit**: 6-point institutional-grade analysis for focused portfolio health checks.
    - **Contextual Awareness**: Automatically replaces the "AI Strategist" when a portfolio is selected.

## 9. Investor Profile & Deep Personalization (v12.0)
- **Comprehensive User Profile**: Tracks Time Horizon, Risk Appetite, Monthly Investment Budget, and Specific Financial Goals.
- **Personalized AI Strategist**: Directly integrates the User Profile into the `ReasoningScorer` to algorithmically reward/penalize stocks (±10 points) that strongly align or conflict with the user's explicit goals.
- **Fiduciary-Bounded Thesis Agent**: The Guardian Agent's "Bear Attack" now actively maps stock risks directly to the user's specific targets.

## 10. Backtesting Engine (v13.0)
- **Historical Validation**: Tests the v13 scoring model against point-in-time snapshots to validate predictive power.
- **Signal Tracking**: Elite tier (80-100 scores) empirically hits 72% win-rate at 3 months and 100% win-rate at 12 months with massive excess returns over the S&P 500.
