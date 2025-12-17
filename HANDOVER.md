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


