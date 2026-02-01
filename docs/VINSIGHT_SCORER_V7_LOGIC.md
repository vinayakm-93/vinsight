# VinSight Scorer v7.4: "The Fundamental Purist"

**Version**: v7.4 (Wealth Manager Logic)
**Date**: Feb 2026
**Target Audience**: Retail Investors with a Quarterly+ Horizon.

## Executive Summary
The VinSight Scorer v7.4 adopts a **"Wealth Manager"** philosophy. The score (0-100) reflects **Business Quality** exclusively. Technicals and AI Projections are relegated to **Risk Gates** that strictly penalize the score but do not add points.

---

## 1. The Core Score (100 Points)
*Philosophy: "If the business does well, the stock eventually follows."*

The score is purely fundamental, weighted as follows:

### A. Valuation (30%)
*Measuring Margin of Safety.*
*   **PEG Ratio (20 pts)**: Price/Earnings to Growth. (Dynamic Benchmark).
*   **Forward PE (10 pts)**: Forward-looking valuation.
*   **Goal**: Avoid overpaying for growth.

### B. Profitability (20%)
*Measuring Economic Moat.*
*   **Operating Margin (10 pts)**: Core business health.
*   **Net Margin (10 pts)**: Bottom-line efficiency.

### C. Efficiency (20%)
*Measuring Management Skill.*
*   **ROE (Return on Equity) (10 pts)**: How well management uses shareholder capital. Target: Sector Specific.
*   **ROA (Return on Assets) (10 pts)**: How efficient the asset base is. Target: Sector Specific.

### D. Solvency (10%)
*Measuring Survival.*
*   **Debt/Equity (5 pts)**: Leverage check.
*   **Current Ratio (5 pts)**: Liquidity check.

### E. Growth (10%)
*Measuring Momentum.*
*   **Earnings Growth QoQ**: Quarterly earnings acceleration.

### F. Conviction (10%)
*Measuring Smart Money Support.*
*   **Institutional Ownership**: High ownership implies validation by funds.

---

## 2. The Risk Gates (Penalties)
*Philosophy: "Don't Force Errors."*

These components **SUBTRACT** points only.

### A. Trend Gate (-15 Points)
*   **Condition**: If `Current Price < SMA 200`.
*   **Logic**: Primary downtrend. "Don't catch a falling knife."

### B. Projection Gate (-15 Points)
*   **Condition**: If Monte Carlo **P10 (Bear Case)** predicts > 15% loss.
*   **Logic**: High volatility or downside risk.

---

## 3. Dynamic Benchmarking (v7.4)
### The 10 Wealth Manager Themes
Instead of granular industries, we consolidate the market into **10 Broad Archetypes**. This ensures every stock gets a robust assessment.

| Theme | Archetype | Key Benchmark Examples |
| :--- | :--- | :--- |
| **High Growth Tech** | High Risk/Reward | PE < 45, Growth > 20% |
| **Mature Tech** | Cash Cows | PE < 25, Margins > 20% |
| **Financials** | Rate Sensitive | PE < 13, High Debt OK |
| **Healthcare** | R&D Defensive | PE < 22, Strong Margins |
| **Consumer Cyclical** | Economy Linked | PE < 20, Med Margins |
| **Consumer Defensive** | Safety | PE < 22, Div Yield Focus |
| **Energy & Materials** | Commodities | PE < 12, High Debt (CapEx) |
| **Industrials** | GDP Linked | PE < 20, Avg Margins |
| **Real Estate** | Yield Focus | PE < 35, High Debt |
| **Utilities** | Bond Proxies | PE < 18, High Debt/Divs |

### Market Reference (S&P 500)
Every report now comparison-shops the stock against:
1.  **Its Theme Target** (e.g., "Is this cheap for a Software company?")
2.  **The S&P 500** (e.g., "Is this cheap compared to the broad market?")

---

## 4. Optimization
**Deep Sentiment Analysis (LLM)** has been disabled for the scorer flow. Sentiment is now a display-only metric (0% weight) and relies on faster news fetching, significantly reducing load times.
