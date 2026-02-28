# VinSight Scoring Engine Documentation

This document describes the evolution and inner workings of the VinSight Scoring Engine, used to provide institutional-grade equity analysis.

## Current Version: v11.0 (Dumb AI, Smart Python)
**Release Date:** February 2026
**Philosophy:** Shifting algebraic evaluation to deterministic Python algorithms, leaving the LLM to only focus on qualitative narrative synthesis and category scaling.

### 1. The Core Equation
The base score (0-100) is deterministically calculated in Python using the AI's 1-10 Category scales (Growth, Valuation, etc.) multiplied by the mathematically rigid weights of the active Persona (e.g. CFA vs Momentum). 

```python
Base Category Score = Python SUM(AI Component Score * Persona Weight)
Final Score = Python MAX(0, Base Category Score - Kill Switch Penalties) * Confidence Discount
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

### 3. Universal Kill Switches (Python Guardrails)
Instead of trusting the LLM to apply caps, Python forcefully injects explicit point deductions visible as "Badges" in the UI before generation finishes:

| Trigger | Penalty | Logic |
|---------|---------|-------|
| **Solvency Risk** | **-20 pts** | Debt/Equity > 2.0 OR Negative FCF |
| **Valuation Trap**| **-15 pts** | P/E > 50 AND Growth < 10% |
| **Broken Trend**  | **-10 pts** | Price < SMA200 (confirmed downtrend) |
| **Revenue Collapse**| **-15 pts** | Revenue Growth < -10% YoY |
| **Bearish News**  | **-10 pts** | Triggered by Groq Intelligence Agent |
| **Low Confidence**| **-50%**  | AI Confidence < 50% triggers massive confidence discount |

### 4. Grounding Validator (Anti-Hallucination)
To protect users from hallucinated data, the `GroundingValidator` module scans all text produced by the LLM. It extracts all percentage claims and metric quotes, comparing them directly to the truth-source metrics dictionary via a `5%` fuzzy match algorithm. If the LLM produces >2 hallucinatory numbers (e.g., claiming a P/E is 800 when it is truly 20), the entire LLM narrative is suppressed before reaching the UI.

### 5. Persona Sensitivity
The scoring is calibrated by the active persona:
- **Value**: Reward Low P/B and Insider Buying, contrarian stance.
- **Growth**: Forgives high P/E if Revenue Growth > 30%.
- **Momentum**: Scored 90% on Price Action/Volume, ignores valuation.
- **CFA**: Balanced, strict on Solvency and Margins.

---

## Evolution History

### v11.0: Dumb AI, Smart Python
The massive architectural shift. Migrated score calculation entirely out of the LLM prompt. Introduced strict Pydantic parsing schemas, algorithmic Python kill switches, and the regex-based Grounding Validator.

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
