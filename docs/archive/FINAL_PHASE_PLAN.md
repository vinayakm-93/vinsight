# VinSight: Final Phase Plan (v10.0 & Beyond)

**Date:** February 02, 2026
**Current Status:** v9.0 (Feature Complete)
**Objective:** Transition from individual stock analysis to holistic portfolio management and multi-asset intelligence.

## Phase 1: The "Everything" Scorer (Multi-Asset)
*Goal: Expand the `vinsight_scorer` to handle ETFs, Crypto, and mutual funds.*

### 1.1 Architecture Changes
*   **Abstract Scorer Class:** Refactor `VinSightScorer` into a base class `BaseScorer`.
*   **Polymorphic Evaluation:**
    *   `EquityScorer(BaseScorer)`: Current v9.0 logic.
    *   `CryptoScorer(BaseScorer)`: Replaces "Debt/EBITDA" with "Network Activity" and "Hash Rate".
    *   `ETFScorer(BaseScorer)`: Focus on "Expense Ratio", "AUM", and "Holdings Concentration".

### 1.2 Configuration Updates
*   **New Benchmarks:** Add `crypto_benchmarks.json` and `etf_benchmarks.json`.
*   **Data Sourcing:** Integrate CoinGecko (Free Tier) or expanded Alpha Vantage support for crypto data.

## Phase 2: Portfolio Intelligence
*Goal: Move from "Stock Picking" to "Portfolio Construction".*

### 2.1 Portfolio Import
*   **APIs:** Integrate **Plaid** (primary) or **SnapTrade** for read-only brokerage connection.
*   **Manual Import:** CSV upload feature for "Export from Fidelity/Robinhood" flows.

### 2.2 Aggregate Scoring ("The Portfolio Score")
*   **Weighted Average:** Calculate a portfolio-level VinSight Score based on position variance.
*   **Diversification Check:** New Veto/Warning logic for sector concentration (e.g., "Warning: 60% allocation to Tech").
*   **Correlation Matrix:** Visual heatmap showing risk concentration between holdings.

## Phase 3: The Conversational Analyst (AI Chat)
*Goal: Allow users to "talk" to their data.*

### 3.1 Chat Interface
*   **UI:** Floating chat widget in bottom-right or dedicated "Analyst" tab.
*   **Context:** Inject current `StockData` and `ScoreResult` into the LLM system prompt.

### 3.2 Query Routing
*   **Router:** Simple keyword or semantic router.
    *   *"Compare NVDA vs AMD"* -> Comparison Tool.
    *   *"Why is the score low?"* -> Extract `verdict_narrative` and `modifications`.
    *   *"What if rates drop?"* -> Trigger `Projections` simulation with new params.

## Phase 4: Infrastructure Hardening
*   **Caching Layer:** Move from in-memory/disk cache to **Redis** (Cloud Memorystore).
*   **Queue System:** Implement **Cloud Tasks** for long-running "Portfolio Scan" jobs.

## Execution Order
1.  **Phase 1 (Multi-Asset)**: Highest value, core scoring differentiator.
2.  **Phase 3 (AI Chat)**: High "wow" factor, leverages existing Groq integration.
3.  **Phase 2 (Portfolio)**: High complexity, requires external API integrations.
