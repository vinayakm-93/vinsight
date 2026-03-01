# VinSight Scoring Engine: Handoff & Implementation Plan

**Date:** February 02, 2026
**Current Version:** v9.0 (Dynamic Benchmark Model)
**Status:** Implemented & Production Ready (with minor version string cleanup needed)

## 1. Context & Architecture

The scoring engine has evolved to an institutional-grade "Composite Model" that weights **Fundamental Quality (70%)** and **Technical Timing (30%)**.

### Key Files
*   **Logic Core:** [`backend/services/vinsight_scorer.py`](file:///Users/vinayak/Documents/Antigravity/Project%201/backend/services/vinsight_scorer.py)
*   **Configuration:** [`backend/config/sector_benchmarks.json`](file:///Users/vinayak/Documents/Antigravity/Project%201/backend/config/sector_benchmarks.json)
*   **Documentation:** [`docs/SCORING_ENGINE.md`](file:///Users/vinayak/Documents/Antigravity/Project%201/docs/SCORING_ENGINE.md)

## 2. Current Implementation Logic

The current code in `vinsight_scorer.py` implements the v9.0 logic.

### Formula
```python
Final Score = (Quality Score * 0.70) + (Timing Score * 0.30)
```

### Verified Components
1.  **Adaptive Fundamentals (Quality - 70%)**:
    *   Scores weighted based on Sector Benchmarks (PEG, FCF Yield, ROE, etc.).
    *   *Implementation Check:* Verifed `_score_quality` loads benchmarks via `_get_benchmarks`.
2.  **Contextual Timing (Timing - 30%)**:
    *   Uses SMA200/SMA50 trends, RSI (40-65 ideal), and Rel Volume.
    *   *Implementation Check:* Verified `_score_timing` logic.
3.  **Veto Kill-Switches**:
    *   **Insolvency**: Interest Coverage < 1.5x => Max Score 40.
    *   **Valuation**: PEG > 4.0 => Max Quality 50.
    *   **Downtrend**: Price < SMA200 & SMA50 => Max Timing 30.
    *   *Implementation Check:* `evaluate()` applies these caps.

## 3. Discrepancies & Immediate Fixes

> [!WARNING]
> **Version Mismatch**: `vinsight_scorer.py` line 108 defines `VERSION = "v8.0 (CFA Composite Model)"`.
> **Action**: Update this to `VERSION = "v9.0 (Dynamic Benchmark Model)"` to match documentation.

## 4. Future Roadmap (The "Score Plan")

### Short Term
1.  **Version String Update**: Fix the `VERSION` constant in `vinsight_scorer.py`.
2.  **Refine RSI Logic**: Ensure the "40-65" bullish zone is strictly adhered to.
3.  **Smart Money Integration**: Finalize robust data for "Institutional Ownership".

### Long Term
1.  **Multi-Asset Scorer**: Expand to Crypto/ETFs.
2.  **Portfolio Scoring**: Score an entire watchlist.
