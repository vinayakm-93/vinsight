# Fix Email Verification - Gmail App Password Update

## Issue
New users not receiving verification codes due to Gmail authentication error:
```
535, '5.7.8 Username and Password not accepted'
```

## Root Cause
1. ✅ **FIXED**: Cloud Run service account lacked IAM permissions to read secrets
2. ⚠️ **TO FIX**: Gmail App Password may be expired or incorrect

## Solution

### Step 1: Generate New Gmail App Password

1. **Go to Google Account Settings:**
   - Visit: https://myaccount.google.com/apppasswords
   - Sign in with your VinSight email account

2. **Enable 2-Step Verification** (if not already enabled):
   - https://myaccount.google.com/security
   - Click "2-Step Verification" and follow the setup

3. **Create App Password:**
   - Return to: https://myaccount.google.com/apppasswords
   - Select app: "Mail"
   - Select device: "Other (Custom name)" → Enter "VinSight Backend"
   - Click **Generate**
   - Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

### Step 2: Update Secrets in Google Secret Manager

Run these commands (replace `YOUR_NEW_APP_PASSWORD` with the generated password):

```bash
cd "/Users/vinayak/Documents/Antigravity/Project 1"

# Update MAIL_PASSWORD
echo -n "YOUR_NEW_APP_PASSWORD" | \
  ./google-cloud-sdk/bin/gcloud secrets versions add MAIL_PASSWORD \
  --data-file=- \
  --project=vinsight-ai

# Update MAIL_USERNAME (if needed)
echo -n "your-email@gmail.com" | \
  ./google-cloud-sdk/bin/gcloud secrets versions add MAIL_USERNAME \
  --data-file=- \
  --project=vinsight-ai

# Update MAIL_FROM (if needed)
echo -n "your-email@gmail.com" | \
  ./google-cloud-sdk/bin/gcloud secrets versions add MAIL_FROM \
  --data-file=- \
  --project=vinsight-ai
```

### Step 3: Update Local backend/.env

```bash
# Edit backend/.env
nano backend/.env
```

Update these lines:
```env
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=YOUR_NEW_APP_PASSWORD
MAIL_FROM=your-email@gmail.com
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
```

### Step 4: Redeploy Backend

```bash
./deploy.sh
```

Or just update the service to pick up new secrets:

```bash
./google-cloud-sdk/bin/gcloud run services update vinsight-backend \
  --region=us-central1 \
  --project=vinsight-ai \
  --update-labels="fix=email-credentials-$(date +%s)"
```

### Step 5: Test Signup

1. Go to your VinSight frontend
2. Try signing up with a new email
3. Check if verification code arrives

## Verify Fix

Check Cloud Run logs for successful email sending:

```bash
./google-cloud-sdk/bin/gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=vinsight-backend AND textPayload=~\"Verification email sent successfully\"" \
  --limit=5 \
  --project=vinsight-ai \
  --format="table(timestamp,textPayload)"
```

## Alternative: Use SendGrid or AWS SES

If Gmail continues to have issues, consider switching to a transactional email service:

- **SendGrid**: Free tier 100 emails/day
- **AWS SES**: $0.10 per 1,000 emails
- **Mailgun**: Free tier 5,000 emails/month

## IAM Permissions Already Fixed ✅

The following IAM permissions have been added:

```bash
Service Account: 656736716364-compute@developer.gserviceaccount.com
Role: roles/secretmanager.secretAccessor

Secrets with access:
- MAIL_USERNAME
- MAIL_PASSWORD
- MAIL_FROM
- DB_PASS
- JWT_SECRET_KEY
- GROQ_API_KEY
- API_NINJAS_KEY
```

## Deployment Status

- ✅ IAM permissions added
- ✅ Backend service restarted (revision vinsight-backend-00071-vbl)
- ⏳ **Waiting for Gmail App Password update**
