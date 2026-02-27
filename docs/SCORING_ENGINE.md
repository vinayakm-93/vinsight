# VinSight Scoring Engine Documentation

This document describes the evolution and inner workings of the VinSight Scoring Engine, used to provide institutional-grade equity analysis.

## Current Version: v10.0 (The Objective Era)
**Release Date:** February 2026
**Philosophy:** "Ruthless Objectivity." A calibrated 10-tier scoring system with explicit penalty badges.

### 1. The Core Equation
The score (0-100) is a reasoned verdict from the AI, weighted by its confidence level.

```python
Final Score = AI Reasoned Score * Confidence Discount
```

### 2. 10-Tier Scoring Rubric
| Score | Rating | Definition |
|-------|--------|------------|
| **90-100** | 🦄 Generational | Perfect setup (Value + Growth + Momentum). Rare. |
| **85-89** | 💎 High Conviction | Institutional quality. Strongest buy signal. |
| **80-84** | 🚀 Strong Buy | Beating expectations. Standard buy. |
| **75-79** | 📈 Buy | Good company, fair price. |
| **70-74** | ✅ Watchlist | Solid but waiting for entry. |
| **60-69** | 🤞 Speculative | High risk/reward or turnaround. |
| **50-59** | 📉 Weak Hold | Dead money or value trap. |
| **40-49** | ⚠️ Underperform | Deteriorating fundamentals. |
| **20-39** | 🛑 Hard Sell | Broken thesis. |
| **0-19** | ☠️ Bankruptcy Risk | Solvency failure likely. |

### 3. Universal Kill Switches (Penalties)
Instead of caps, we apply explicit point deductions visible as "Badges" in the UI:

| Trigger | Penalty | Logic |
|---------|---------|-------|
| **Solvency Risk** | **-20 pts** | Debt/Equity > 2.0 OR Negative FCF |
| **Valuation Cap** | **-15 pts** | P/E > 50 AND Growth < 10% |
| **Momentum Crash**| **-10 pts** | Price < SMA200 (confirmed downtrend) |
| **Revenue Decline**| **-15 pts** | Revenue Growth < -10% YoY |
| **Low Confidence** | **-50%** | AI Confidence < 50% triggers massive discount |

### 4. Persona Sensitivity
The scoring is calibrated by the active persona:
- **Value**: Penalizes P/B > 3.0, Rewards Dividends.
- **Growth**: Forgives high P/E if PEG < 1.0.
- **Momentum**: Penalizes low RSI/Volume, ignores valuation.
- **CFA**: Balanced, strict on Solvency and Margins.

---

## Evolution History

### v10.0: Objectivity & Transparency
Moved to a 10-tier universal rubric, replaced "caps" with explicit visible penalties, and added confidence weighting to the score.

### v9.0: The Dynamic Benchmark Model
Introduced adaptive sector benchmarks and linear interpolation for scoring.

### v8.0: The CFA Weighted Composite Model
Introduced the 70/30 weighting and the concept of "Kill Switches" (Vetos).

### v7.4: The Fundamental Purist
Focused exclusively on business quality.

### v2.2: Hybrid Sentiment & PEG Integration
Included first-generation sentiment analysis.

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
