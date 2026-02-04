# VinSight Project Handover (v9.0)
**Date:** February 02, 2026
**Status:** Feature Complete / Production Ready
**Target Audience:** PM, Software Engineering, DevOps, and Business Teams.

---

## 1. Executive Summary & Vision (PM / Business)
VinSight is an institutional-grade stock analysis platform designed for serious retail investors and portfolio managers. It moves beyond simple "buy/sell" ratings by providing a **CFA-aligned 70/30 Weighted Composite Model** (Quality vs. Timing).

**The Core Value Prop:**
*   **Adaptive Intelligence**: Scorer v9.0 uses dynamic benchmarking. It knows that a 15% margin for a Software company is "average," but for a Retailer, it's "elite."
*   **Sentiment Sentinel**: Proprietary multi-stage news analysis (Finnhub → Groq Llama 3) with "Spin Detection" to cut through PR noise.
*   **Institutional Transparency**: Distinguishes between discretionary "Real" insider trades and automatic "Boring" 10b5-1 plans.

---

## 2. Product Roadmap & Strategic Features (PM)
### v9.0 Milestones:
- [x] **Dynamic Benchmarking Engine**: Elimination of static targets. Thresholds recalibrate based on 12+ industry themes.
- [x] **Unified Analysis UI**: Compact, high-density dashboard. 40% reduction in vertical footprint for professional efficiency.
- [x] **Strategy Mixer**: Real-time user-adjustable weighting with automatic "Strategy Labeling" (e.g., Value Purist).
- [x] **Projections 2.0**: Monte Carlo simulations with P10/P50/P90 probability curves and analyst consensus overlays.

### Future Backlog Suggestions:
*   **Portfolio Import**: Sync with Plaid/Interactive Brokers APIs.
*   **Multi-Asset Support**: Expand scoring logic to Crypto/ETFs.
*   **AI Chat Interface**: Allow users to query the analyst persona (e.g., "Compare NVDA margins to AMD").

---

## 3. Engineering Deep Dive (Software Engineering)
### Tech Stack
*   **Frontend**: Next.js 15+, TypeScript, Tailwind CSS (v4), Recharts.
*   **Backend**: FastAPI (Python 3.11), SQLAlchemy, NumPy (Vectorized MC simulations).
*   **AI Core**: Groq (Llama 3.3 70B), Gemini 1.5 Pro.
*   **Data Sources**: yfinance (Technical/Consensus), Finnhub (Smart Money/News), Alpha Vantage (Global Financials).
*   **Earnings Intelligence API**: 🛑 **Blocked on Free Tier**.
    *   API Ninjas & FMP both require Premium for transcripts.
    *   **Workaround**: Manual transcript paste feature (Future Work).

### Core Logic: `vinsight_scorer.py`
The heart of the app is the `VinSightScorer` class.
*   **`evaluate()`**: Orchestrates Data fetching → Quality Scoring → Timing Scoring → Veto Checks → Narrative Generation.
*   **Dynamic Interpolation**: Uses `_linear_score()` to map raw values into weighted points based on benchmarks in `backend/config/sector_benchmarks.json`.
*   **Vetos**: Hard kill-switches (e.g., Interest Coverage < 1.5x) cap the total score.

---

## 4. DevOps & Infrastructure (DevOps)
### Deployment Flow
We use a custom `./deploy.sh` script that automates the Google Cloud Run workflow.
1.  **Containerization**: Backend and Frontend are containerized.
2.  **Memory**: **CRITICAL**: Backend requires **2GiB RAM** to handle Python ML overhead.
3.  **Networking**: Next.js uses a rewrite proxy in `next.config.ts` to forward `/api/*` to the backend, solving CORS and cookie issues.

### Environment & Secrets (GCP Secret Manager)
| Secret Name | Purpose |
|-------------|---------|
| `GROQ_API_KEY` | Deep Reasoning & Sentiment |
| `FINNHUB_API_KEY` | Institutional Data / Real-time News |
| `DATABASE_URL` | Cloud SQL (PostgreSQL) connection string |
| `JWT_SECRET` | Authentication tokens |

---

## 5. Business & Operations (Business Team)
### Licensing
*   **Model**: **Source Available License**.
*   **Rights**: Modification and redistribution are restricted. The code is owned by Vinayak.

### API Cost Management
The app is currently configured for maximum performance on **Free/Low-Cost tiers**:
*   **Finnhub**: Free tier (60 calls/min) - We use defensive caching.
*   **Groq**: Extremely high-speed, low-cost LLM inference.
*   **yfinance**: Zero cost.
*   **Gemini**: Free tier / Pay-per-use for deep earnings analysis.

### Compliance & Reliability
*   **Data Latency**: Institutional filings are updated via 13F (quarterly) and Form 4 (90-day window).
*   **Error Handling**: Implemented custom `NaNJSONResponse` to prevent crashes when financial data is missing from providers.

---
**Handover Signature:**
*Vinayak*
*Lead Architect*
