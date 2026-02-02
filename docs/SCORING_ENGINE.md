# VinSight Scoring Engine Documentation

This document describes the evolution and inner workings of the VinSight Scoring Engine, used to provide institutional-grade equity analysis.

## Current Version: v9.0 (The Dynamic Benchmark Model)
**Release Date:** February 2026
**Philosophy:** "Institutional Precision." Adaptive intelligence that recalibrates thresholds based on 12+ industry themes.

### 1. The Core Equation
The score (0-100) is a weighted average of Fundamental Quality and Technical Timing.

```python
Final Score = (Quality Score * 0.70) + (Timing Score * 0.30)
```

| Factor | Weight | Scoring Mechanism |
| :--- | :--- | :--- |
| **Quality Score** | 70% | Linear Interpolation against **Sector Benchmarks** |
| **Timing Score** | 30% | Linear Interpolation against **Volatility (Beta) Context** |

### 2. Adaptive Fundamentals (Quality)
*Philosophy: "A 15% margin is weak for Software, but elite for Retail."*

The following metrics are dynamically adjusted based on the stock's classified theme:

| Metric | Ideal (Max Pts) | Zero (0 Pts) |
| :--- | :--- | :--- |
| **PEG Ratio** | `sector_peg_fair` | `sector_peg_fair + 2.0` |
| **FCF Yield** | `sector_fcf_yield_strong` | `sector_fcf_yield * 0.2` |
| **ROE** | `sector_roe_strong` | `sector_roe * 0.3` |
| **Net Margin** | `sector_margin_healthy`| `sector_margin * 0.4` |
| **Debt/EBITDA**| `sector_debt_safe` | `sector_debt * 2.0` |
| **Rev Growth** | `sector_growth_strong` | `0.0%` |

### 3. Contextual Timing
*Philosophy: "Trend is relative to volatility."*

- **Beta Score**: Targets are shifted based on the `beta_safe` benchmark for that sector.
- **RSI Support**: Interpretation of 40-65 zone persists, with volume confirmation relative to sector liquidity.

### 4. Kill Switches (Vetos)
Vetos override the weighted average to cap the maximum possible score if a fatal flaw is detected:

1.  **Insolvency Veto**: `Interest Coverage < 1.5x`. Score capped at **40 (Strong Sell)**.
2.  **Valuation Veto**: `PEG Ratio > 4.0`. Quality Score capped at **50**.
3.  **Downtrend Veto**: `Price < SMA200` AND `Price < SMA50`. Timing Score capped at **30**.

---

## Evolution History

### v8.0: The CFA Weighted Composite Model
Introduced the 70/30 weighting and the concept of "Kill Switches" (Vetos). Moved away from simple additive sums to a institutional-style composite score.

### v7.4: The Fundamental Purist
Focused exclusively on business quality (Valuation, Profitability, Efficiency, Solvency). Technicals were used only as negative "Risk Gates" (subtracting points) but could not add points.

### v2.2: Hybrid Sentiment & PEG Integration
Included first-generation sentiment analysis (FinBERT + Groq) and integrated the PEG ratio to correctly score growth stocks.

---

## Sector Benchmarks (Themes)
VinSight dynamically maps stocks to 12+ Wealth Manager Themes:
- 💻 Tech & Growth
- 💾 Semiconductors
- 🏢 Blue Chips
- 💰 Financials
- 🏥 Healthcare
- 🛍️ Consumer Discretionary
- 🛒 Consumer Staples
- 🛢️ Energy & Materials
- 🏗️ Industrials
- ⚡ Utilities
- 🧱 Materials & Mining
- 🏠 Real Estate (REITs)
- 🌱 Small Caps
