# Alert System Fix - Deployment Guide

## Issue Identified

Your production environment is showing the **old code** with browser alerts. The error "Failed to create alert" suggests the backend might be returning an error, but we need to:

1. ✅ Deploy the updated AlertModal.tsx with toast notifications
2. ✅ Deploy the updated alerts.py with proper limit enforcement
3. 🔍 Investigate the backend error

## Pre-Deployment Checklist

Before deploying, verify:

### 1. Check if changes are committed to git

```bash
cd /Users/vinayak/Documents/Antigravity/Project\ 1
git status
```

### 2. Review the changes to be deployed

**Frontend Changes:**
- `/frontend/src/components/AlertModal.tsx` - Toast notifications + limit display

**Backend Changes:**
- `/backend/routes/alerts.py` - Monthly trigger limit enforcement

## Deployment Steps

### Option 1: Full Deployment (Recommended)

Run the deployment script to deploy both frontend and backend:

```bash
cd /Users/vinayak/Documents/Antigravity/Project\ 1
./deploy.sh
```

**Note:** This will:
- Build and deploy the backend Docker image with the updated alerts.py
- Build and deploy the frontend Docker image with the updated AlertModal.tsx
- Update CORS settings
- Take approximately 5-10 minutes

### Option 2: Frontend Only (Faster)

If you only want to deploy the UI fixes:

```bash
cd /Users/vinayak/Documents/Antigravity/Project\ 1
export PATH="$(pwd)/google-cloud-sdk/bin:$PATH"
cd frontend

# Build
gcloud builds submit --tag gcr.io/vinsight-ai/vinsight-frontend .

# Deploy
gcloud run deploy vinsight-frontend \\
    --image gcr.io/vinsight-ai/vinsight-frontend \\
    --platform managed \\
    --region us-central1 \\
    --allow-unauthenticated
```

### Option 3: Backend Only

If you need to deploy the limit enforcement:

```bash
cd /Users/vinayak/Documents/Antigravity/Project\ 1
export PATH="$(pwd)/google-cloud-sdk/bin:$PATH"
cd backend

# Build
gcloud builds submit --tag gcr.io/vinsight-ai/vinsight-backend .

# Deploy (make sure to load secrets from .env first)
source .env
gcloud run deploy vinsight-backend \\
    --image gcr.io/vinsight-ai/vinsight-backend \\
    --platform managed \\
    --region us-central1 \\
    --allow-unauthenticated \\
    --set-env-vars ENV=production \\
    --set-secrets="DB_PASS=DB_PASS:latest,JWT_SECRET_KEY=JWT_SECRET_KEY:latest,GROQ_API_KEY=GROQ_API_KEY:latest,API_NINJAS_KEY=API_NINJAS_KEY:latest,MAIL_PASSWORD=MAIL_PASSWORD:latest,MAIL_USERNAME=MAIL_USERNAME:latest,MAIL_FROM=MAIL_FROM:latest"
```

## Post-Deployment Testing

After deployment:

1. Visit your production URL: https://vinsight-frontend-wddr2kfz3a-uc.a.run.app
2. Login to your account
3. Select a stock (e.g., AAPL)
4. Click the bell icon (🔔)
5. Verify:
   - ✅ You see the monthly limit usage display
   - ✅ Creating an alert shows a toast notification (not browser alert)
   - ✅ Toast is green and says "Alert set for..."
   - ✅ If you've hit your limit, you see a clear error message

## Debugging Backend Errors

If you still get "Failed to create alert" after deployment:

### Check Backend Logs

```bash
export PATH="$(pwd)/google-cloud-sdk/bin:$PATH"
gcloud run services logs read vinsight-backend --limit 100 --region us-central1
```

### Common Issues

1. **Database connection**: Verify Cloud SQL is configured correctly
2. **Authentication**: Ensure JWT tokens are working
3. **Monthly limit reached**: User may have actually hit their limit
4. **Active alerts limit**: User may have 50 active alerts already

### Manual Test

Try creating an alert via curl to see the exact error:

```bash
# Replace YOUR_TOKEN with actual JWT token from browser cookies
curl -X POST https://vinsight-backend-YOUR-URL.run.app/api/alerts/ \\
  -H "Content-Type: application/json" \\
  -H "Cookie: session=YOUR_TOKEN" \\
  -d '{
    "symbol": "AAPL",
    "target_price": 250.0,
    "condition": "above"
  }'
```

## Rollback Plan

If deployment causes issues:

```bash
export PATH="$(pwd)/google-cloud-sdk/bin:$PATH"

# Find previous revision
gcloud run revisions list --service vinsight-frontend --region us-central1

# Rollback (replace REVISION_NAME)
gcloud run services update-traffic vinsight-frontend \\
  --to-revisions REVISION_NAME=100 \\
  --region us-central1
```
