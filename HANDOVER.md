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

## ⚠️ Critical Limitations
### 1. Database Persistence (SQLite)
Currently, the app uses **SQLite** stored inside the container.
*   **The Issue:** Google Cloud Run file systems are *ephemeral*. When the container stops (scales to zero) or you deploy a new version, **the file system is wiped**.
*   **Effect:** User accounts, watchlists, and cached data will disappear on every redeploy.
*   **Future Fix:** Migrate to **Cloud SQL (PostgreSQL)**.

### 2. Cold Starts
*   Since we are on the "Free Tier" (scaling to 0), the first request after a while might take 10-20 seconds to wake up the server.

---

## 📂 Key Files Guide
| File | Purpose |
|------|---------|
| `deploy.sh` | **Master deployment script.** Run this to ship changes. |
| `backend/Dockerfile` | Defines backend environment. Optimized for CPU Torch. |
| `frontend/Dockerfile` | Defines frontend build. Accepts build-args for API URL. |
| `CONTRIBUTING.md` | Guide for other developers (Fork & Pull Request model). |
| `.dockerignore` | Prevents huge local files (venv, node_modules) from uploading. |

---

## 🔮 Future Roadmap
1.  **Cloud SQL**: Move `finance.db` to a managed PostgreSQL instance for permanent storage.
2.  **Secret Manager**: Move `.env` secrets (like API keys) to Google Secret Manager instead of hardcoding or checking them in.
3.  **CI/CD**: Connect GitHub Actions to run `deploy.sh` automatically when you push to `main`.
