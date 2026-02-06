#!/bin/bash
# Script to add EODHD_API_KEY to Google Cloud Secret Manager
# Run this script to securely store the EODHD API key for production deployment

set -e

PROJECT_ID="vinsight-ai"
# Check for API_KEY env var
if [ -z "$EODHD_API_KEY" ]; then
    echo -ne "${YELLOW}Enter your EODHD API Key: ${NC}"
    read -r API_KEY
    if [ -z "$API_KEY" ]; then
        echo "Error: API_KEY is required."
        exit 1
    fi
else
    API_KEY=$EODHD_API_KEY
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up EODHD API Key in Google Cloud Secret Manager${NC}"
echo "Project: $PROJECT_ID"
echo "Secret Name: $SECRET_NAME"
echo ""

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

# Set project
echo -e "${GREEN}Setting active project...${NC}"
gcloud config set project $PROJECT_ID

# Enable Secret Manager API
echo -e "${GREEN}Enabling Secret Manager API...${NC}"
gcloud services enable secretmanager.googleapis.com

# Check if secret already exists
if gcloud secrets describe $SECRET_NAME &> /dev/null; then
    echo -e "${YELLOW}Secret $SECRET_NAME already exists. Adding new version...${NC}"
    echo -n "$API_KEY" | gcloud secrets versions add $SECRET_NAME --data-file=-
    echo -e "${GREEN}✅ New version added to existing secret${NC}"
else
    echo -e "${GREEN}Creating new secret $SECRET_NAME...${NC}"
    echo -n "$API_KEY" | gcloud secrets create $SECRET_NAME --data-file=-
    echo -e "${GREEN}✅ Secret created successfully${NC}"
fi

# Grant Cloud Run service account access to the secret
echo -e "${GREEN}Granting Cloud Run access to secret...${NC}"
SERVICE_ACCOUNT=$(gcloud iam service-accounts list --filter="email~compute@developer.gserviceaccount.com" --format="value(email)")

if [ -z "$SERVICE_ACCOUNT" ]; then
    echo -e "${YELLOW}Warning: Could not find default compute service account${NC}"
    echo "You may need to grant access manually:"
    echo "gcloud secrets add-iam-policy-binding $SECRET_NAME \\"
    echo "  --member='serviceAccount:YOUR_SERVICE_ACCOUNT' \\"
    echo "  --role='roles/secretmanager.secretAccessor'"
else
    gcloud secrets add-iam-policy-binding $SECRET_NAME \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/secretmanager.secretAccessor"
    echo -e "${GREEN}✅ Access granted to: $SERVICE_ACCOUNT${NC}"
fi

echo ""
echo -e "${GREEN}✅ EODHD API Key setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Update deploy.sh to include EODHD_API_KEY in --set-secrets"
echo "2. Run ./deploy.sh to deploy with the new secret"
echo ""
echo "To verify the secret:"
echo "gcloud secrets versions access latest --secret=$SECRET_NAME"
