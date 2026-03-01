# Research Note: Vinsight Scoring Engine v12.0 Proposal

**Status**: Draft / Internal Proposal
**Author**: Antigravity (AI Architect)
**Date**: 2026-02-28

## Objective
To resolve the "False Positive" penalty issues identified in v11.0 (e.g., AMD scoring 40/100 despite strong underlying fundamentals) by transitioning from deterministic Python "Kill Switches" to Contextual AI-Driven Judgment.

---

## 1. The Core Problem: Python's Lack of Context
The v11.0 architecture uses "Dumb AI, Smart Python" logic to ensure mathematical grounding. However, the Python "Kill Switches" are *too* binary:
- **Solvency Risk (-20 pts)**: Fires on `Debt/Equity > 2.0` or `Negative FCF`. 
- **The AMD Case**: AMD has near-zero debt and positive FCF, but a data gap (None/0.0 FCF) triggered a bankruptcy-level penalty.
- **The Inconsistency**: The AI narrative correctly identified "Strong AI Demand," but the final score was crushed by a hard-coded Python rule that ignored the sector context (Semi-conductors/Growth).

---

## 2. Proposed v12.0 Architecture: Hybrid Judgment

### A. Python Layer (Objective Flagging)
Python remains the source of truth for raw math but loses the power to unilaterally apply lethal penalties.
- **Role**: Calculate Base Score (0-100) and flag "Penalty Candidates."
- **Example**: If `P/E > 50`, Python flags a `VALUATION_TRAP_CANDIDATE` but does NOT subtract points yet.

### B. LLM Layer (Contextual Decider)
The LLM receives the flags and the full context (Earnings Call, Sector, Relative Valuations).
- **Role**: Decide whether to *apply* or *waive* the penalty based on qualitative context.
- **Example**: "P/E is 100, but Forward PEG is 0.8 and AI growth is 100%. **WAIVE** Valuation Trap penalty."

### C. Safety Guardrails (Pydantic Validation)
- Every penalty waiver must include a `reasoning` string.
- If AI confidence is low (< 60%), the system defaults to the safe/pessimistic Python penalty.

---

## 3. Data Integrity Strategy

### Missing Data Policy
- **No AI Search**: LLMs should NOT be used to "Google" missing financial data (Latency and Hallucination risks).
- **Provider Fallback**: Implement a Python-level fallback (e.g., if yFinance fails, try FMP or Alpha Vantage).
- **Neutral Defaulting**: Missing data should be treated as "Neutral" (5/10) rather than "Zero/Negative" to prevent catastrophic score collapses on data gaps.

---

## 4. Logical Grounding vs. Number Grounding
Current "Grounding" validates that LLM numbers match input data. **Real Grounding (v12.0)** must validate that the LLM's *narrative logic* is consistent with the data trends (e.g., the AI cannot say "Stable margins" if the data shows a 10% drop).

---

## Conclusion
Moving the "Kill Switch" logic from Python to the AI (with structured guardrails) transforms Vinsight from a spreadsheet with a chat window into a **Contextual Investment Analyst**.
