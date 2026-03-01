# VinSight Scoring Engine v11.1

> **Authority**: Python is the sole numerical score authority. The LLM provides narrative analysis and a bounded ±10 contextual adjustment.

## Architecture

```
StockData ──► _compute_components() ──► 5 scores (0-10)
                                            │
                                  _apply_persona_weights()
                                            │
                                     Base Score (0-100)
                                            │
                                  _compute_penalties()
                                            │
                                  Penalized Score (0-100)
                                            │
                              ┌─────────────┴─────────────┐
                              │   LLM (Groq/OpenRouter)   │
                              │  Narrative + ±10 adjust   │
                              └─────────────┬─────────────┘
                                            │
                                     Final Score (0-100)
```

## 1. Components (0-10 each)

| Component | Metrics | Ideal → 10 | Zero → 0 |
|-----------|---------|------------|----------|
| **Valuation** | PEG, FCF Yield, Forward P/E | PEG ≤ 1.0, FCF ≥ 8%, Fwd P/E ≤ 10 | PEG ≥ 3.5, FCF ≤ 0, Fwd P/E ≥ 50 |
| **Profitability** | ROE, Net Margin, Op Margin | ROE ≥ 25%, NM ≥ 20%, OM ≥ 30% | ROE ≤ 0%, NM ≤ 0%, OM ≤ 0% |
| **Health** | D/E, Interest Coverage, Current Ratio, Altman Z | D/E ≤ 0.3, IC ≥ 15, CR ≥ 3, Z ≥ 3 | D/E ≥ 3, IC ≤ 1, CR ≤ 0.5, Z ≤ 1.8 |
| **Growth** | Rev Growth 3Y, EPS Surprise, Earnings QoQ | RevG ≥ 20%, EPS ≥ 5%, EarG ≥ 15% | RevG ≤ -10%, EPS ≤ -5%, EarG ≤ -15% |
| **Technicals** | Price/SMA200, Price/SMA50, RSI, Rel Volume, Dist to High | Above SMAs, RSI 40-60, High Vol | Below SMAs, RSI extreme, Low Vol |

**None handling**: `_linear_score(None)` → `None`. `_score_component` averages only non-None values. All-None → neutral 5.0.

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

## 4. LLM Role

The LLM receives the full Python component breakdown in its prompt and provides:

| Field | Type | Purpose |
|-------|------|---------|
| `thought_process` | string | 300-400 word analysis |
| `summary.verdict` | string | 1-sentence action |
| `summary.bull_case` | string | Upside drivers (100-150 words) |
| `summary.bear_case` | string | Downside risks (100-150 words) |
| `contextual_adjustment` | int (-10 to +10) | Qualitative score nudge |
| `adjustment_reasoning` | string | Mandatory explanation (>20 chars or adjustment is zeroed) |

**The LLM does NOT determine the score.** Its `contextual_adjustment` is bounded and requires reasoning.

## 5. Response Shape

```json
{
  "score": 72,
  "rating": "Watchlist Buy",
  "color": "#22c55e",
  "justification": "VERDICT: ... BULL: ... BEAR: ...",
  "structured_summary": { "verdict", "bull_case", "bear_case", "fundamental_analysis", "technical_analysis" },
  "raw_breakdown": { "Quality Score": 65.2, "Timing Score": 70.0 },
  "component_scores": { "valuation": 6.5, "profitability": 7.2, "health": 8.1, "growth": 5.8, "technicals": 7.0 },
  "algo_breakdown": { "Quality Score": 62, "Timing Score": 68 },
  "score_explanation": { "factors": [...], "opportunities": [...] },
  "contextual_adjustment": 3,
  "adjustment_reasoning": "Strong earnings guidance and AI demand catalysts justify upward adjustment.",
  "penalty_details": [{ "type": "Overvaluation", "severity": 4.2, "detail": "..." }],
  "guardian_trigger": false,
  "meta": { "source", "persona", "timestamp_pst", "primary_driver", "thought_process", "engine_version": "v11.1" },
  "details": [...]
}
```

## 6. What Was Cleaned / Removed

| Removed | Reason |
|---------|--------|
| Confidence score & UI Meter | Cosmetic 0.8-1.0 multiplier with no mathematical signal value. |
| Strategy Mixer slider | Extraneous piece of UI replaced entirely by the Persona Selector. |
| Binary kill switches | Step-functions cause chaotic score drops; replaced by continuous Buffer+Gradient penalties. |
| TextBlob Sentiment | Yielded low-quality sentiment noise; Groq/LLM provides much better contextual analysis. |
| LLM scoring authority | LLM hallucinated math and weights; Python determinism is now the sole source of truth. |
| `None → 0` coercion | Missing data artificially crushed scores; it now cleanly skips components without penalizing. |

## 7. What Was Implemented & Fixed

| Feature / Fix | Description |
|---------------|-------------|
| **5-Component Deterministic Base** | Python now flawlessly computes Valuation, Profitability, Health, Growth, Technicals as 0-10 scores, multiplied by explicit Persona Weights to generate the raw score. |
| **Buffer + Gradient Penalties** | Penalties (like having a P/E of 50) don't apply until they cross a significant outlier threshold (the "Buffer"), after which they smoothly ramp up. This prevents tiny market jitter from affecting the score. |
| **Data Integrity & Fallbacks** | Fixed the massive bug where `None` data wiped out scores. The engine gracefully ignores missing data and averages what remains. |
| **LLM Grounding Guardrail Fix** | The `GroundingValidator` was falsely suppressing the AI narrative (e.g. for Amazon) because it couldn't see the penalty math. It has been fixed to read the full `StockData` context, stopping the false "hallucination mismatch" warnings. |
| **F-String Output Bug Fix** | Re-wrote the nested `{{}}` JSON dumps syntax that caused the LLM server to crash entirely due to an unhashable dict error. |
| **LLM Adjustment (±10)** | The LLM no longer dictates the entire 0-100 score. It provides qualitative narrative analysis, and only has authority to nudge the deterministic python score by a maximum of ±10 points (which requires 20+ chars of reasoning). |

## 7. Files Modified

| File | Changes |
|------|---------|
| `vinsight_scorer.py` | `_linear_score`, `_score_component`, `_compute_components`, `PERSONAS`, `_apply_persona_weights`, `PENALTY_SENSITIVITY`, `_compute_penalties` |
| `reasoning_scorer.py` | `AIResponseSchema`, `_parse_response`, `_build_system_prompt`, `_build_context` |
| `analysis.py` | TextBlob removed, fallback returns neutral |
| `requirements.txt` | `textblob` removed |
| `Dashboard.tsx` | Confidence meter, strategy slider removed; v11.1 labels |
| `test_scoring_v11_1.py` | 18 tests: None handling, components, personas, penalties, integration |

## 8. Running Tests

```bash
cd backend && python3 -m pytest tests/test_scoring_v11_1.py -v
```

Expected: 18/18 passed in <0.1s.
