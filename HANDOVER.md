# VinSight Project Handover (v12.0 - v12 Engine)
**Date:** March 23, 2026
**Status:** **Stable** (Advanced AI Reasoning & Stability Patched)
**Target Audience:** Engineering Team / Next Agent

---

## 1. Executive Summary
This release (v12.0) introduces the **v12 Engine**, a hybrid intelligence architecture that suppresses mathematical variance in favor of grounded AI reasoning. We resolved critical timeout issues by aligning frontend expectations with backend LLM latency.

- **V12 Reasoning**: The `ReasoningScorer` is now the primary authority. It incorporates User Profiles (Goals/Horizon) into a qualitative adjustment layer.
- **Stability**: Fixed `NoneType` crashes in the data coordinator and implemented strict provider-level timeouts (30s) to prevent hangs.
- **Zero-Stall UX**: Initial "Phase 1" responses now include narrative placeholders to prevent the UI from flickering or stalling on "Analyzing...".

---

## 2. Key Technical Changes
- **Timeouts**: Increased to **180s** (3 minutes) in the frontend. Reasoning models (DeepSeek R1) are given maximum headroom.
- **Data Coordination**: `finance.py` now robustly handles Yahoo Finance null/empty fields using `(obj or {}).get()` patterns.
- **Modularity**: Extracted the "Algorithmic Score Breakdown" into a reusable UI component.

---

## 3. Current State
- **System**: Stable.
- **Performance**: 180s reasoning window ensures accurate deep-thought processing.
- **Reliability**: Proactive narrative fallbacks ensure the UI is always readable, even during background generation.

---

## 4. Next Session Instructions (Context Prompt)
*Copy and paste this into the next chat to retain context:*

> **SYSTEM CONTEXT RESTORE: VinSight v12.0.0 (v12 Reasoning Engine)**
>
> **Current Architecture:**
> -   **Scoring Engine**: `v12.0` Reasoning Engine. Python computes the base; LLM provides narrative + goal-aligned adjustments (±10).
> -   **Response Schema**: Includes `structured_summary` (verdict, bull, bear, fundamental, technical) for all responses.
> -   **Network thresholds**: 180s Frontend timeout. 30s/15s internal LLM failover timeouts.
> -   **Data Safety**: Coordinated fetcher is null-safe against Yahoo Finance partial responses.
>
> **Rules:**
> 1.  **Narrative Integrity**: Always maintain the `structured_summary` shape in API responses.
> 2.  **Performance Check**: Ensure LLM providers don't exceed the 30s per-hop threshold.
> 3.  **UI Consistency**: Use `renderAlgoBreakdown` for scoring transparency across tabs.

---
**Handover Signature:**
*VinSight AI / Antigravity Agent (v12.0 Final)*

