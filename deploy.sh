#!/bin/bash
set -e

# Configuration
PROJECT_ID="vinsight-ai"
REGION="us-central1"
BACKEND_SERVICE="vinsight-backend"
FRONTEND_SERVICE="vinsight-frontend"

# Colors
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Deployment to Google Cloud Project: $PROJECT_ID${NC}"

# Add local gcloud to PATH if it exists
if [ -d "./google-cloud-sdk/bin" ]; then
    export PATH="$(pwd)/google-cloud-sdk/bin:$PATH"
fi

# Check for gcloud
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed."
    echo "Install it: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# 1. Setup
echo -e "${GREEN}Setting active project...${NC}"
gcloud config set project $PROJECT_ID
echo -e "${GREEN}Enabling APIs...${NC}"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com containerregistry.googleapis.com artifactregistry.googleapis.com

# 2. Deploy Backend
# Load secrets from backend/.env (using source for safety with special chars)
if [ -f backend/.env ]; then
  echo "Loading secrets from backend/.env..."
  set -a
  source backend/.env
  set +a
  echo "Debug: Loaded MAIL_USERNAME length: ${#MAIL_USERNAME}"
  echo "Debug: Loaded MAIL_PASSWORD length: ${#MAIL_PASSWORD}"
  echo "Debug: Loaded MAIL_FROM length: ${#MAIL_FROM}"
  echo "Debug: Loaded JWT_SECRET_KEY length: ${#JWT_SECRET_KEY}"
else 
  echo "WARNING: backend/.env not found!"
fi

# Cloud SQL Configuration
if [ -z "$CLOUDSQL_INSTANCE" ]; then
    echo "CLOUDSQL_INSTANCE not set in .env. Attempting auto-detection..."
    # Attempt to find the first instance in the project
    DETECTED_TO_USE=$(gcloud sql instances list --format="value(connectionName)" --limit=1 2>/dev/null)
    if [ -n "$DETECTED_TO_USE" ]; then
        echo "Auto-detected Cloud SQL Instance: $DETECTED_TO_USE"
        CLOUDSQL_INSTANCE=$DETECTED_TO_USE
    fi
fi

DB_URL_VAL="sqlite:///./finance.db"
CLOUD_SQL_FLAG=""

if [ -n "$CLOUDSQL_INSTANCE" ]; then
    echo -e "${GREEN}Configuring for Cloud SQL: $CLOUDSQL_INSTANCE${NC}"
    
    # Check for DB Credentials
    if [ -z "$DB_USER" ] || [ -z "$DB_PASS" ]; then
        echo "ERROR: DB_USER and DB_PASS must be set in backend/.env for Cloud SQL deployment."
        echo "Please add them and retry."
        exit 1
    fi
    
    DB_NAME=${DB_NAME:-"finance"} # Default to finance if not set
    # Connection string for Google Cloud Run (Unix Socket)
    DB_URL_VAL="postgresql+psycopg2://$DB_USER:$DB_PASS@/$DB_NAME?host=/cloudsql/$CLOUDSQL_INSTANCE"
    CLOUD_SQL_FLAG="--add-cloudsql-instances $CLOUDSQL_INSTANCE"
else
    echo -e "${GREEN}WARNING: No Cloud SQL instance configured. Deploying with Ephemeral SQLite.${NC}"
fi

echo -e "${GREEN}Deploying Backend...${NC}"
cd backend
gcloud builds submit --tag gcr.io/$PROJECT_ID/$BACKEND_SERVICE .
gcloud run deploy $BACKEND_SERVICE \
    --image gcr.io/$PROJECT_ID/$BACKEND_SERVICE \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 2Gi \
    --set-env-vars ENV=production,CLOUDSQL_INSTANCE="$CLOUDSQL_INSTANCE",DB_USER="$DB_USER",MAIL_SERVER="$MAIL_SERVER",MAIL_PORT="$MAIL_PORT" \
    --set-secrets="DB_PASS=DB_PASS:latest,JWT_SECRET_KEY=JWT_SECRET_KEY:latest,GROQ_API_KEY=GROQ_API_KEY:latest,API_NINJAS_KEY=API_NINJAS_KEY:latest,MAIL_PASSWORD=MAIL_PASSWORD:latest,MAIL_USERNAME=MAIL_USERNAME:latest,MAIL_FROM=MAIL_FROM:latest" \
    $CLOUD_SQL_FLAG

BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE --platform managed --region $REGION --format 'value(status.url)')
if [ -z "$BACKEND_URL" ]; then
    echo "Error: Failed to get Backend URL. Deployment failed."
    exit 1
fi
echo -e "${GREEN}Backend is live at: $BACKEND_URL${NC}"

# 2.1 Deploy Market Watcher Job
echo -e "${GREEN}Deploying Market Watcher Job...${NC}"
gcloud run jobs deploy vinsight-watcher \
    --image gcr.io/$PROJECT_ID/$BACKEND_SERVICE \
    --region $REGION \
    --command "python" \
    --args "jobs/market_watcher_job.py" \
    --set-env-vars ENV=production,CLOUDSQL_INSTANCE="$CLOUDSQL_INSTANCE",DB_USER="$DB_USER",MAIL_SERVER="$MAIL_SERVER",MAIL_PORT="$MAIL_PORT" \
    --set-secrets="DB_PASS=DB_PASS:latest,JWT_SECRET_KEY=JWT_SECRET_KEY:latest,GROQ_API_KEY=GROQ_API_KEY:latest,API_NINJAS_KEY=API_NINJAS_KEY:latest,MAIL_PASSWORD=MAIL_PASSWORD:latest,MAIL_USERNAME=MAIL_USERNAME:latest,MAIL_FROM=MAIL_FROM:latest" \
    --set-cloudsql-instances "$CLOUDSQL_INSTANCE"

cd ..

# 3. Deploy Frontend (with Backend URL)
echo -e "${GREEN}Deploying Frontend...${NC}"
cd frontend

# Create temporary cloudbuild.yaml to pass build-args correctly
cat > cloudbuild.yaml <<EOF
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', 'gcr.io/$PROJECT_ID/$FRONTEND_SERVICE', '.']
images:
- 'gcr.io/$PROJECT_ID/$FRONTEND_SERVICE'
EOF

echo -e "${GREEN}Building Frontend...${NC}"
gcloud builds submit --config cloudbuild.yaml .
rm cloudbuild.yaml # Cleanup

gcloud run deploy $FRONTEND_SERVICE \
    --image gcr.io/$PROJECT_ID/$FRONTEND_SERVICE \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars "MY_BACKEND_URL=$BACKEND_URL,API_URL=$BACKEND_URL"

FRONTEND_URL=$(gcloud run services describe $FRONTEND_SERVICE --platform managed --region $REGION --format 'value(status.url)')
echo -e "${GREEN}Frontend is live at: $FRONTEND_URL${NC}"

# Update Backend to allow requests from the new Frontend URL (CORS)
echo -e "${GREEN}Updating Backend CORS to trust Frontend...${NC}"
gcloud run services update $BACKEND_SERVICE \
    --platform managed \
    --region $REGION \
    --update-env-vars ALLOWED_ORIGINS="$FRONTEND_URL",FRONTEND_URL="$FRONTEND_URL"

echo -e "${GREEN}Deployment Complete!${NC}"
echo "Frontend: $FRONTEND_URL"
echo "Backend:  $BACKEND_URL"
