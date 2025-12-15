# Deployment Guide: GitHub & Google Cloud Run

## 1. Push to GitHub
First, we need to secure your code in a GitHub repository.

1.  **Initialize Git** (if not done):
    ```bash
    git init
    git add .
    git commit -m "Initial commit for Google Cloud Migration"
    ```

2.  **Create Repository**:
    - Go to [GitHub.com/new](https://github.com/new)
    - Name it `vinsight-app` (or similar).
    - **Do NOT** check "Add README" or "Add .gitignore" (we already have them).

3.  **Push**:
    ```bash
    git remote add origin https://github.com/YOUR_USERNAME/vinsight-app.git
    git branch -M main
    git push -u origin main
    ```

---

## 2. Deploy to Google Cloud Run
We will deploy the **Backend** first, then the **Frontend**.

### Prerequisites
- Install [Google Cloud CLI](https://cloud.google.com/sdk/docs/install).
- Login: `gcloud auth login`
- Set Project: `gcloud config set project YOUR_PROJECT_ID`

### A. Deploy Backend
1.  **Configure Env Vars**:
    You MUST set your secrets in Cloud Run.
    When deploying, add flags for each secret:
    ```bash
    gcloud run deploy vinsight-backend \
      --source . \
      --set-env-vars JWT_SECRET_KEY=secret,GROQ_API_KEY=key,API_NINJAS_KEY=key \
      --region us-central1 \
      --allow-unauthenticated
    ```

2.  **Build & Deploy**:
    *Note: If asked to enable APIs (Artifact Registry, Cloud Run), say **Yes** (y).*

2.  **Get URL**:
    - Google will print the Service URL (e.g., `https://vinsight-backend-xyz.a.run.app`).
    - **Copy this URL**.

### B. Deploy Frontend
1.  **Update Config**:
    - Open `frontend/.env.production` (create if missing).
    - Add: `NEXT_PUBLIC_API_URL=https://vinsight-backend-xyz.a.run.app` (The URL you just got).

2.  **Build & Deploy**:
    ```bash
    cd ../frontend
    gcloud run deploy vinsight-frontend \
      --source . \
      --region us-central1 \
      --allow-unauthenticated
    ```

### C. Final Check
- Visit the **Frontend URL** provided by Google.
- It should load and talk to your Backend!

---

## 3. Important Notes
- **Database**: Currently effectively "read-only" because Cloud Run wipes changes to `finance.db` on restart. Even if you "add stocks", they will disappear after a while.
- **Fixing Database**: Create a Cloud SQL (Postgres) instance on Google Cloud and set the `DATABASE_URL` environment variable in your Backend Cloud Run service settings.
