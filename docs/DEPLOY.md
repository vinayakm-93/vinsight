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
*Required Secrets:* `DB_PASS`, `JWT_SECRET_KEY`, `GROQ_API_KEY`, `API_NINJAS_KEY`, `MAIL_PASSWORD`.

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
