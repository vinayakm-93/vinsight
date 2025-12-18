# Deployment Guide

We use a unified script `deploy.sh` to handle building, secrets mounting, and deploying to Google Cloud Run.

## Prerequisites
1.  **Google Cloud SDK**: [Install Here](https://cloud.google.com/sdk/docs/install)
2.  **Login**:
    ```bash
    gcloud auth login
    gcloud config set project vinsight-ai
    ```

## One-Click Deploy
To deploy Backend, Frontend, and Background Jobs:
```bash
./deploy.sh
```

> [!IMPORTANT]
> **Frontend API Proxy Configuration**: The `frontend/next.config.js` contains the backend URL for API proxying.
> - In **production**, it uses the Cloud Run backend URL: `https://vinsight-backend-wddr2kfz3a-uc.a.run.app`
> - In **development**, it uses localhost: `http://127.0.0.1:8000`
> - The switch is automatic based on `NODE_ENV`
> - **If deploying to a different backend URL**, update the production URL in `next.config.js` before deploying!

## First Time Setup (If Redeploying elsewhere)

### 1. Database Setup (Cloud SQL)
You must create a PostgreSQL instance and user.
```bash
# Create Instance
gcloud sql instances create vinsight-db --tier=db-f1-micro --region=us-central1

# Create DB & User
gcloud sql databases create finance --instance=vinsight-db
gcloud sql users create vinsight --instance=vinsight-db --password=YOUR_PASSWORD
```

### 2. Secrets Management
Store sensitive keys in Google Secret Manager:
```bash
# Use our helper script to upload local .env vars
python3 scripts/migrate_secrets.py
```
*Required Secrets:* `DB_PASS`, `JWT_SECRET_KEY`, `GROQ_API_KEY`, `FINNHUB_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `API_NINJAS_KEY`, `MAIL_PASSWORD`.

### 3. Initialize Schema
Run the initialization script locally (connected via Proxy) or via a one-off Cloud Run Job task to create tables.
```bash
# Connect locally to test
./google-cloud-sdk/bin/gcloud sql connect vinsight-db --user=vinsight
```

### 4. Scheduler Setup
The `vinsight-watcher` job needs a trigger to run periodic checks.
```bash
gcloud scheduler jobs create http vinsight-market-trigger \
  --schedule="*/5 9-16 * * 1-5" \
  --time-zone="America/New_York" \
  --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/vinsight-ai/jobs/vinsight-watcher:run" \
  --http-method=POST \
  --oauth-service-account-email=YOUR_SA_EMAIL \
  --location=us-central1
```

## Troubleshooting

### 500 Internal Server Error / Watchlist Stocks "Loading..."

**Symptoms**: All API calls return 500, watchlist stock prices show "Loading..." indefinitely.

**Cause**: The frontend `next.config.js` proxy is pointing to the wrong backend URL. This happens if:
- The config was accidentally set to localhost (`http://127.0.0.1:8000`) for production
- The `NODE_ENV` check was removed or broken

**Solution**:
1. Check `frontend/next.config.js` and verify the production URL is correct:
   ```javascript
   const apiUrl = process.env.NODE_ENV === 'production' 
       ? 'https://vinsight-backend-wddr2kfz3a-uc.a.run.app'  // Must be Cloud Run URL
       : 'http://127.0.0.1:8000';
   ```
2. Redeploy the frontend after fixing.

**Verification**: Test the proxy is working in production:
```bash
curl -s https://vinsight-frontend-wddr2kfz3a-uc.a.run.app/api/data/quote/AAPL
# Should return JSON stock quote, not "Internal Server Error"
```

---

### "Failed to load watchlists" / 404 Errors

**Cause**: Next.js proxy strips trailing slashes. FastAPI by default redirects to trailing-slash URLs via 307, but cookies are lost during redirect.

**Solution** (Already Applied):
1. `main.py` has `redirect_slashes=False` in FastAPI config
2. Routes use dual decorators: `@router.get("")` and `@router.get("/")`

---

### View Backend Logs
```bash
export PATH="$(pwd)/google-cloud-sdk/bin:$PATH"
gcloud run services logs read vinsight-backend --region us-central1 --limit 50
```
