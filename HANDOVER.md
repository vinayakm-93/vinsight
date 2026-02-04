# VinSight Project Handover (v9.3 - AI vs. Algo Split)
**Date:** February 04, 2026
**Status:** **Production Ready** (SMTP + Dual Scoring)
**Target Audience:** Engineering Team / Next Agent

---

## 1. Executive Summary
The system has been matured to a **Dual-Layer Analysis** architecture. It now differentiates between the **AI's subjective conviction** and the **Algorithmic ground truth**. SMTP messaging is confirmed working, and service health-checks are integrated.

---

## 2. Completed Work
### Scoring Architecture
- **AI Reasoning**: The top section displays scores generated from the LLM's own internal logic + component ratings (0-10).
- **Algo Baseline (v9.0)**: The bottom section (Algorithmic Breakdown) uses the strict 70/30 mathematical engine. It is explicitly labeled as the "Foundation" with v9.0 versioning.
- **Separation**: Fixed a mapping bug where AI and Algo sections were showing identical scores. They now diverge properly based on the model's subjective view.

### Reliability & Infrastructure
- **SMTP Fixed**: Confirmed functional mail delivery through Gmail SMTP (App Passwords).
- **Health Checks**: New `validate_keys.py` script verifies health of Groq, Gemini, Serper, Finnhub, and EODHD.
- **Support**: Backend `mail.py` now supports both `MAIL_` and `SMTP_` prefixes.

---

## 3. Current State
- **System**: Stable and Depolyed.
- **Primary AI**: Llama 3.3 70B (Groq) / Gemini 1.5 Flash (Fallback).
- **Email Service**: Live.

---

## 4. Next Session Instructions (Context Prompt)
*Copy and paste this into the next chat to retain context:*

> **SYSTEM CONTEXT RESTORE: VinSight v9.3**
>
> **Current State:**
> -   **Dual Scoring**: `raw_breakdown` = AI Conviction; `algo_breakdown` = Mathematical Engine (v9.0). Use these keys specifically in the UI.
> -   **SMTP**: Functional using `SMTP_USERNAME` and `SMTP_PASSWORD` in `.env`.
> -   **Validation**: Run `python backend/validate_keys.py` to check service connectivity.
>
> **Rules:**
> 1.  Maintain the separation of AI Briefing (Top) and Algo Baseline (Bottom).
> 2.  Do NOT hardcode keys; use Secret Manager for Cloud and `.env` for Local.
> 3.  Keep the "v9.0 Foundation" tag on the bottom breakdown table.

---
**Handover Signature:**
*Antigravity Agent (Session Final)*
