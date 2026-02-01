# Vinsight Project Handover

**Date:** February 01, 2026
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
*   **Updates (v6.7.2):** Insider Activity Refinement (3-Level Hierarchy), Institutional Smart Money UI.

### Backend
*   **Path:** `/backend`
*   **Tech:** Python (FastAPI), PyTorch (CPU-only), Gunicorn.
*   **Database:** Cloud SQL (PostgreSQL).
*   **Key Libraries:** `transformers` (AI analysis), `yfinance` (Stock data), `simplejson` (NaN handling).
*   **Deployment:** Docker container on Cloud Run (**Requires 2Gi Memory**).

---

## 🚀 How to Deploy
We have automated the deployment process.

1.  **Make your changes** in code.
2.  **Run the script**:
    ```bash
    ./deploy.sh
    ```
    *This script handles enabling APIs, building images, and deploying with correct memory config.*

---

## ⚠️ Infrastructure Notes (Jan 22)
### 1. Memory Requirements
*   **Critical**: The Backend service now requires **2Gi** of memory (up from 512MiB) due to `torch` and `transformers` usage.
*   **Configuration**: This is enforced in `./deploy.sh` via the `--memory 2Gi` flag.

### 2. Cold Starts
*   Since we are on the "Free Tier" (scaling to 0), the first request after a while might take 10-20 seconds to wake up the server.

---

## 📂 Key Files Guide
| File | Purpose |
|------|---------|
| `deploy.sh` | **Master deployment script.** Handles Secrets, Cloud SQL, Memory Config. |
| `backend/main.py` | Core App. Includes `NaNJSONResponse` for robust serialization. |
| `backend/services/alert_checker.py` | Auto-deletes triggered alerts to keep queue clean. |
| `backend/Dockerfile` | Defines backend environment. Optimized for CPU Torch. |
| `frontend/Dockerfile` | Defines frontend build. |

---

## ✅ Deployment Status Report (Jan 23)
| Component | Status | Verified Date | Notes |
|-----------|--------|---------------|-------|
| **Frontend** | 🟢 Stable | Feb 01 | Insider 3-Level UI, Monte Carlo Projections. |
| **Backend** | 🟢 Stable | Feb 01 | Heuristic 10b5-1 logic, Smart Money Signal. |
| **Database** | 🟢 Stable | Jan 22 | Alert deletion logic active. |
| **Alerts** | 🟢 Active | Jan 22 | Creation & Auto-Deletion verified. |

## ⚠️ Resolved Issues (Feb 01)
### 1. Insider Signal Noise
*   **Cause**: Automatic stock grants/gifts were diluting the "Insider Sentiment" signal.
*   **Fix**: Implemented strict filtering: only "Open Market" discretionary trades now drive the Signal/Score.
*   **UI**: Added "Type" column and "Real vs Auto" breakdown for transparency.

## ⚠️ Resolved Issues (Jan 22)
### 1. Alert Creation "Failed"
*   **Cause**: `NaN` values crashing JSON encoder.
*   **Fix**: Implemented `NaNJSONResponse`.

### 2. OOM Crashes
*   **Cause**: 512MiB memory insufficient for ML libs.
*   **Fix**: Upgraded container to 2Gi RAM.

### 3. Trailing Slash 404
*   **Cause**: Frontend proxy stripped slashes, Backend expected them.
*   **Fix**: Backend routes updated to be slash-agnostic via `@router.post("")`.

---
