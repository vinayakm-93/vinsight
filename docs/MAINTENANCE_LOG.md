# VinSight Maintenance & Incident Log

This document records major system fixes, Root Cause Analyses (RCAs), and architectural optimizations.

## [2026-02-01] Yahoo Finance Rate Limit RCA
**Issue:** Stocks failing to load with "Too Many Requests" (HTTP 429) error.
**Root Cause:** Yahoo's `query1` endpoint aggressively blocks requests without modern browser TLS fingerprints and proper User-Agents.
**Resolution:** 
- Switched to `query2.finance.yahoo.com`.
- Implemented `curl_cffi` style handling (by allowing `yfinance` to manage its own session).
- Added aggressive 1-hour caching to reduce redundant calls.
**Files:** `backend/services/yahoo_client.py` (legacy fallback), `backend/services/finance.py`.

## [2026-01-29] Alert System Overhaul
**Issue:** Alert notifications were using `alert()` (blocked by browsers) and limits weren't enforced.
**Fixes:**
- Replaced all JS `alert()` calls with a dynamic Toast notification system (green/red/blue).
- **Limit Enforcement:** Added backend checks for Monthly Trigger Limit (default 10) and Active Alert Count (max 50).
- **UI:** Added usage progress bars to the Alert Modal.
**Files:** `frontend/src/components/AlertModal.tsx`, `backend/routes/alerts.py`.

## [2024-12-15] Sentiment Bias Fix (v2.2)
**Issue:** Sentiment analysis was biased ~89% positive due to financial news "spin".
**Fixes:**
- Enabled Groq AI (Llama 3.3 70B) by default for deep reasoning.
- Implemented Bearish Keyword Detection (25+ terms like "layoffs", "miss", "loss").
- **Spin Detection:** Penalizes score if bearish keywords are present but sentiment label is positive.
- Raised positive threshold from 0.3 to 0.5.
**Result:** Reduced positive bias from 89% to 33%.

## [Ongoing] Email Credential Security
**Issue:** Hardcoded credentials or insecure storage.
**Status:** Unified under Google Secret Manager for production and `.env` for local. Ensure `SMTP_SERVER` and `SMTP_PORT` are correctly configured in `.env`.

---

### Legend
- **RCA:** Root Cause Analysis
- **Hotfix:** Immediate patch for production-breaking bug
- **Maint:** Routine cleanup or optimization
