# Vinsight Project Handover

**Date:** December 15, 2025
**Status:** Deployed to Production (Google Cloud Run)

## 🔗 Quick Links
- **GitHub Repository:** [vinayakm-93/vinsight](https://github.com/vinayakm-93/vinsight)
- **Live Frontend:** [https://vinsight-frontend-wddr2kfz3a-uc.a.run.app](https://vinsight-frontend-wddr2kfz3a-uc.a.run.app)
- **Live Backend:** [https://vinsight-backend-wddr2kfz3a-uc.a.run.app](https://vinsight-backend-wddr2kfz3a-uc.a.run.app)
- **Google Cloud Console:** [Project: vinsight-ai](https://console.cloud.google.com/home/dashboard?project=vinsight-ai)

---

## 🛠️ Architecture Overview
This is a monorepo containing both the Frontend and Backend.

### Frontend
*   **Path:** `/frontend`
*   **Tech:** Next.js (React), TypeScript, Tailwind CSS.
*   **Deployment:** Docker container on Cloud Run.
*   **Configuration:** `NEXT_PUBLIC_API_URL` is baked in at build time via `deploy.sh`.

### Backend
*   **Path:** `/backend`
*   **Tech:** Python (FastAPI), PyTorch (CPU-only), Gunicorn.
*   **Database:** SQLite (`finance.db`).
*   **Key Libraries:** `transformers` (AI analysis), `yfinance` (Stock data).
*   **Deployment:** Docker container on Cloud Run.

---

## 🚀 How to Deploy
We have automated the deployment process.

1.  **Make your changes** in code.
2.  **Run the script**:
    ```bash
    ./deploy.sh
    ```
    *This script handles enabling APIs, building Docker images, and deploying to Cloud Run.*

---

## ⚠️ Known Limitations
### 1. Cold Starts
*   Since we are on the "Free Tier" (scaling to 0), the first request after a while might take 10-20 seconds to wake up the server.

---

## 📂 Key Files Guide
| File | Purpose |
|------|---------|
| `deploy.sh` | **Master deployment script.** Handles Secrets, Cloud SQL, Jobs, and Cloud Run. |
| `backend/Dockerfile` | Defines backend environment. Optimized for CPU Torch. |
| `frontend/Dockerfile` | Defines frontend build. Accepts build-args for API URL. |
| `backend/jobs/` | Contains background job scripts (e.g. `market_watcher_job.py`). |
| `scripts/` | Database and Secret migration utilities. |

---

## 🔮 Future Roadmap
1.  **Redis Caching**: Use Redis for even faster alerts and user session management.
2.  **AI Agents**: Upgrade `vinsight-watcher` to use Vertex AI for qualitative analysis (News/Sentiment) instead of just price thresholds.
3.  **CI/CD**: Connect GitHub Actions to run `deploy.sh` automatically on push.

---


## 🛡️ Security & Infrastructure (Dec 16 Update)
### ✅ Completed Upgrades
*   **Database**: Migrated to **Google Cloud SQL (PostgreSQL)**. Data is now persistent.
*   **Secrets**: All sensitive keys (`DB_PASS`, `API_KEYS`) are stored in **Google Secret Manager**.
*   **Background Jobs**: `MarketWatcher` moved to **Cloud Run Jobs** + **Cloud Scheduler**.
*   **Hardening**:
    *   `/test` route disabled in production.
    *   Strict CORS and Rate Limiting enabled.

### 🔄 Architecture Update (Dec 16 - Auth Fix)
*   **Proxy Layer**: Implemented **Next.js Rewrites** to proxy API requests.
    *   **Why?** To solve Third-Party Cookie blocking on Chrome/Safari when Frontend and Backend are on different Cloud Run subdomains.
    *   **Flow**: Browser -> Frontend (`/api/*`) -> Backend (`/api/*`).
    *   **Benefit**: Cookies are now "First-Party" and secure.

### ✨ Use Experience (Dec 16)
*   **Favicon**: Updated with custom brand icon.
*   **Auth Flow**: Verified Login/Signup logic with new Proxy architecture.

## ✅ Deployment Status Report
| Component | Status | Verified Date | Notes |
|-----------|--------|---------------|-------|
| **Frontend** | 🟢 Stable | Dec 16 | Uses Proxy for API calls. Favicon updated. |
| **Backend** | 🟢 Stable | Dec 16 | Served via standard port 8080. |
| **Database** | 🟢 Stable | Dec 16 | Cloud SQL Connection healthy. |
| **Auth** | 🟢 Stable | Dec 16 | Cookies setting correctly via Proxy. |
| **Watchlist** | 🟢 Stable | Dec 16 | Self-healing logic added for default lists. |

## ⚠️ Known Issues & Workarounds (Dec 16)
### 1. Hardcoded Proxy URL
*   **Issue**: `next.config.js` `rewrites()` function was failing to read `API_URL` environment variable at runtime in Cloud Run.
*   **Workaround**: We have temporarily hardcoded the backend URL (`https://vinsight-backend-wddr2kfz3a-uc.a.run.app`) in `frontend/next.config.js`.
*   **Future Fix**: Investigate why Cloud Run environment variable injection is delayed or hidden from Next.js build context vs runtime context.

### 2. Watchlist Empty State
*   **Fix**: Added logic in `backend/routes/watchlist.py` to automatically create "My First List" if a user has 0 watchlists. This prevents the UI from entering a broken state.

### 3. Trailing Slash Redirect (Dec 16 Fix)
*   **Issue**: Watchlists failed to load after login with "Not Found" or "Failed to load watchlists" errors.
*   **Root Cause**: Next.js proxy strips trailing slashes. FastAPI was redirecting via 307, but cookies were lost during redirect.
*   **Solution**:
    1. Added `redirect_slashes=False` to FastAPI in `main.py`
    2. Added dual route decorators (`@router.get("")` and `@router.get("/")`) in `watchlist.py`
*   **Status**: ✅ Fixed and deployed.

---

## ✨ Recent Features (Dec 16)
*   **Guest Mode**: Users can explore the app without logging in. Guest watchlist saved to localStorage.
*   **Improved UI States**: Loading, error, and empty states for better UX.

---

## 🧠 VinSight Score v6.1 Update (Dec 17)

### Rebalanced for Retail Investors
Fundamentals now carry **60%** of the total score.

| Pillar | Points | Key Components |
|--------|--------|----------------|
| **Fundamentals** | 60 | Valuation (16), Growth (14), Margins (14), Debt (8), Inst (4), Flow (4) |
| **Sentiment** | 15 | News (10 pts) + Finnhub MSPR (5 pts) |
| **Projections** | 15 | Monte Carlo upside (9 pts) + risk/reward (6 pts) |
| **Technicals** | 10 | SMA distance (4), RSI optimal zone (3), volume (3) |

### Sector Override Feature
- 29 industry-specific benchmarks with wide variance
- Dropdown in Recommendation Score header (moved from Fundamentals)
- P/E median ranges: 8 (Mining) → 80 (EV/Clean Energy)

### Expanded Sector Benchmarks (v6.1)
| Sector | P/E Median | PEG Fair | Growth % | Margin % |
|--------|------------|----------|----------|----------|
| Technology | 30 | 2.0 | 15% | 20% |
| Cloud/SaaS | 60 | 3.5 | 25% | 15% |
| EV/Clean Energy | 80 | 4.0 | 35% | 5% |
| Banks | 12 | 1.2 | 8% | 30% |
| Mining | 8 | 1.0 | 5% | 15% |

### Outlook Time Horizons
- **3 Months**: Technical/Momentum (RSI, SMA50, Sentiment, Beta)
- **6 Months**: Valuation/Growth (PEG, P/E, SMA200, Earnings Growth)
- **12 Months**: Quality/Fundamentals (Margins, Debt, 52W Range, Dividends)

### New Environment Variable
```
FINNHUB_API_KEY=  # Free from finnhub.io
```

