#!/bin/bash
PROJECT_ID="vinsight-ai"
# Attempt to find gcloud path from the same logic as deploy.sh
if [ -d "./google-cloud-sdk/bin" ]; then
    export PATH="$(pwd)/google-cloud-sdk/bin:$PATH"
fi

gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=vinsight-backend" --limit 50 --format="table(timestamp,textPayload)"
