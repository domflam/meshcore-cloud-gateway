#!/usr/bin/env bash
set -euo pipefail
PROJECT_ID="${PROJECT_ID:-meshcore-cloud-gateway}"
LOCATION="${LOCATION:-europe-west1}"
BUCKET="${TF_STATE_BUCKET:-${PROJECT_ID}-tfstate}"
cd "$(dirname "$0")/.."

if ! gcloud storage buckets describe "gs://${BUCKET}" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "Creating GCS Terraform state bucket: gs://${BUCKET}"
  gcloud storage buckets create "gs://${BUCKET}" \
    --project="$PROJECT_ID" \
    --location="$LOCATION" \
    --uniform-bucket-level-access
else
  echo "State bucket exists: gs://${BUCKET} (verify ownership and IAM)"
fi
gcloud storage buckets update "gs://${BUCKET}" --versioning
terraform init -reconfigure \
  -backend-config="bucket=${BUCKET}" \
  -backend-config="prefix=terraform/meshcore-cloud-gateway"
echo "Remote state initialized in gs://${BUCKET}/terraform/meshcore-cloud-gateway"
