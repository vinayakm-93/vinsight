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

# Check gcloud
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
echo -e "${GREEN}Deploying Backend...${NC}"
cd backend
gcloud builds submit --tag gcr.io/$PROJECT_ID/$BACKEND_SERVICE .
gcloud run deploy $BACKEND_SERVICE \
    --image gcr.io/$PROJECT_ID/$BACKEND_SERVICE \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars ENV=production,DATABASE_URL="sqlite:///./finance.db"

BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE --platform managed --region $REGION --format 'value(status.url)')
echo -e "${GREEN}Backend is live at: $BACKEND_URL${NC}"
cd ..

# 3. Deploy Frontend (with Backend URL)
echo -e "${GREEN}Deploying Frontend...${NC}"
cd frontend

# Create temporary cloudbuild.yaml to pass build-args correctly
cat > cloudbuild.yaml <<EOF
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '--build-arg', 'NEXT_PUBLIC_API_URL=$BACKEND_URL', '-t', 'gcr.io/$PROJECT_ID/$FRONTEND_SERVICE', '.']
images:
- 'gcr.io/$PROJECT_ID/$FRONTEND_SERVICE'
EOF

echo -e "${GREEN}Building Frontend with API_URL=$BACKEND_URL...${NC}"
gcloud builds submit --config cloudbuild.yaml .
rm cloudbuild.yaml # Cleanup

gcloud run deploy $FRONTEND_SERVICE \
    --image gcr.io/$PROJECT_ID/$FRONTEND_SERVICE \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated

FILES_URL=$(gcloud run services describe $FRONTEND_SERVICE --platform managed --region $REGION --format 'value(status.url)')
echo -e "${GREEN}Frontend is live at: $FILES_URL${NC}"
cd ..

echo -e "${GREEN}Deployment Complete!${NC}"
echo "Frontend: $FILES_URL"
echo "Backend:  $BACKEND_URL"
