# VinSight Scoring Engine v13.0

> **Authority**: Python is the sole numerical score authority. Three independent axes (Quality, Value, Timing) are scored 0-100 and combined via persona-weighted conviction. The LLM provides narrative analysis and a bounded ±10 contextual adjustment.

## Architecture

```
StockData ──► evaluate_v13(persona, guardian_status)
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
     Quality(0-100) Value(0-100) Timing(0-100)
     ROE, Margins   PEG, P/E    SMA, RSI
     D/E, EPS Stab  FCF Yield   Volume, Mom
     ROIC, Altman Z RIM MoS
          │          │          │
          └──────────┼──────────┘
                     ▼
           Conviction = Q×Wq + V×Wv + T×Wt
                     │
          ┌──────────┴──────────┐
          │  Guardian Modifiers │
          │ BROKEN→cap(40)     │
          │ AT_RISK→-10pts     │
          └──────────┬──────────┘
                     │
          ┌──────────┴──────────┐
          │   LLM (Groq/etc)   │
          │  Narrative + ±10   │
          └──────────┬──────────┘
                     │
               Final Score (0-100)
```

## 1. Three-Axis Decomposition (v13 NEW)

| Axis | Metrics | Score Range | Purpose |
|------|---------|-------------|---------|
| **Quality** | ROE, Net/Op Margin, D/E, ICR, Altman Z, EPS Stability, ROIC Spread | 0-100 | Business quality without valuation |
| **Value** | PEG, Forward P/E, FCF Yield, RIM Margin of Safety | 0-100 | Cheapness / valuation attractiveness |
| **Timing** | Price vs SMA50/200, RSI, Relative Volume, Momentum | 0-100 | Technical entry signal |

### Persona Conviction Weights

| Persona | Quality (Wq) | Value (Wv) | Timing (Wt) |
|---------|-------------|------------|-------------|
| **CFA** | 45% | 30% | 25% |
| **Momentum** | 10% | 10% | 80% |
| **Value** | 25% | 50% | 25% |
| **Growth** | 45% | 25% | 30% |
| **Income** | 50% | 30% | 20% |

**Formula**: `conviction = (quality × Wq) + (value × Wv) + (timing × Wt)`

## 2. Legacy Components (0-10 each, still used within axes)


| Component | Metrics | Ideal → 10 | Zero → 0 |
|-----------|---------|------------|----------|
| **Valuation** | PEG, FCF Yield, Forward P/E | PEG ≤ 1.0, FCF ≥ 8%, Fwd P/E ≤ 10 | PEG ≥ 3.5, FCF ≤ 0, Fwd P/E ≥ 50 |
| **Profitability** | ROE, Net Margin, Op Margin | ROE ≥ 25%, NM ≥ 20%, OM ≥ 30% | ROE ≤ 0%, NM ≤ 0%, OM ≤ 0% |
| **Health** | D/E, Interest Coverage, Current Ratio, Altman Z | D/E ≤ 0.3, IC ≥ 15, CR ≥ 3, Z ≥ 3 | D/E ≥ 3, IC ≤ 1, CR ≤ 0.5, Z ≤ 1.8 |
| **Growth** | Rev Growth 3Y, EPS Surprise, Earnings QoQ | RevG ≥ 20%, EPS ≥ 5%, EarG ≥ 15% | RevG ≤ -10%, EPS ≤ -5%, EarG ≤ -15% |
| **Technicals** | Price/SMA200, Price/SMA50, RSI, Rel Volume, Dist to High | Above SMAs, RSI 40-60, High Vol | Below SMAs, RSI extreme, Low Vol |

**None handling (V13 Refactor)**: `_linear_score(None)` intercepts missing metric data, returning `points = None` and `status = 'Skipped'`. The metric's maximum points sink natively and never penalize the denominator.

**The 50% Fiduciary Refusal Rule**: An explicit data integrity threshold. If an entire mathematical Axis (Quality, Value, Timing) is starved of more than 50% of its data points from APIs (e.g. `available_pts < 50.0`), the algorithm explicitly aborts the score aggregation and neutralizes the entire axis to `50.0`. This prevents edge-case microcaps and missing IPO data from generating bizarre zero-denominator inflations, ensuring a heavily documented, predictable flat fallback.

## 2. Persona Weights

| Persona | Valuation | Profitability | Health | Growth | Technicals |
|---------|-----------|---------------|--------|--------|------------|
| **CFA** | 25% | 25% | 20% | 15% | 15% |
| **Momentum** | 5% | 5% | 5% | 15% | 70% |
| **Value** | 40% | 15% | 20% | 10% | 15% |
| **Growth** | 10% | 10% | 5% | 55% | 20% |
| **Income** | 15% | 20% | 35% | 10% | 20% |

**Formula**: `base_score = Σ (component × 10 × weight%)`  → 0-100 scale.

## 3. Continuous Penalties (Buffer + Gradient)

Penalties are designed to aggressively punish true outliers while ignoring normal market variance (noise). They use a Buffer + Gradient mathematical pattern.

1.  **Buffer Zone (0 points):** Minor deviations within this zone are forgiven as normal variance. 
2.  **Gradient Zone (Proportional scaling):** Once the buffer is crossed, the penalty scales linearly up to the maximum deduction.
3.  **Persona Multiplier:** The calculated penalty is finally multiplied by the user's Persona Sensitivity weight.

| Penalty | Buffer Zone | Gradient Ends At | Max Deduction | Notes |
|---------|-------------|------------------|---------------|-------|
| **Solvency** | D/E < 2.0x Safe | D/E = 4.0x Safe | -20 pts | e.g. If safe is 1.0, 1.9 is forgiven. |
| **Overvaluation** | P/E < 2.0x Median | P/E = 4.0x Median | -15 pts | Halved if Rev Growth > 15% |
| **Broken Trend** | Price > -5% SMA200| Price = -20% SMA200 | -10 pts | 3% dip forgiven; 12% dip penalized. |
| **Revenue Decline** | RevG > -10% | RevG = -30% | -15 pts | -5% miss forgiven; -25% penalized. |

**Persona sensitivity multipliers** (applied to raw penalty):

| Persona | Solvency | Overvaluation | Trend | Revenue |
|---------|----------|---------------|-------|---------|
| CFA | 1.0 | 1.0 | 1.0 | 1.0 |
| Momentum | 0.3 | 0.2 | 1.5 | 0.3 |
| Value | 1.2 | 1.5 | 0.5 | 1.0 |
| Growth | 0.5 | 0.3 | 0.8 | 1.5 |
| Income | 1.5 | 0.8 | 0.5 | 1.2 |

## 4. LLM Narrative Layer & Contextual Nudges

The LLM (DeepSeek R1 / Llama 3.3) receives the full Three-Axis Breakdown (Quality, Value, Timing) and generates a structural narrative:
- **Thought Process**: 300-400 word deep reasoning chain.
- **Summary**: Bull Case, Bear Case, and Verdict.
- **Contextual Adjustment (±10)**: The LLM does NOT determine the base score. It only provides a qualitative nudge (e.g., +3 points for strong AI catalysts) which must be justified.

## 5. Response Shape (v13 Schema)

```json
{
  "score": 72,
  "rating": "Watchlist Buy",
  "color": "#22c55e",
  "quality_axis": 85.2,
  "value_axis": 62.3,
  "timing_axis": 71.0,
  "conviction_weights": { "Q": 0.45, "V": 0.30, "T": 0.25 },
  "justification": "VERDICT: ... BULL: ... BEAR: ...",
  "structured_summary": {
    "verdict": "...", "bull_case": "...", "bear_case": "...",
    "fundamental_analysis": "...", "technical_analysis": "...",
    "persona_lens": "The CFA philosophy rates this stock 72/100 because..."
  },
  "raw_breakdown": { "Quality Score": 85.2, "Value Score": 62.3, "Timing Score": 71.0 },
  "algo_breakdown": { "Quality Score": 85, "Value Score": 62, "Timing Score": 71 },
  "contextual_adjustment": 3,
  "adjustment_reasoning": "Strong earnings guidance and AI demand catalysts justify upward adjustment.",
  "penalty_details": [{ "type": "Overvaluation", "severity": 4.2, "detail": "..." }],
  "guardian_trigger": false,
  "meta": { "source": "...", "persona": "CFA", "timestamp_pst": "...", "engine_version": "v13.0" }
}
```

## 6. Files Modified (v13 Engine)

| File | Changes |
|------|---------|
| `backend/services/vinsight_scorer.py` | Contains `evaluate_v13()`, `_compute_quality_axis()`, `_compute_value_axis()`, `_compute_timing_axis()`, and Persona weights. |
| `backend/services/reasoning_scorer.py` | Fetches Guardian status, injects User Profiles, builds v13 context prompt, and enforces bounding. |
| `backend/services/backtest.py` | Historical validation of the Three-Axis Model using point-in-time snapshots. |
| `backend/services/data_provider.py` | Abstract `DataProvider` interface for agnostic data fetching. |

## 7. Running Tests
```bash
cd backend && python3 -m pytest tests/ -v
```

Expected: 18/18 passed in <0.1s.
