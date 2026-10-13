#!/usr/bin/env bash
set -euo pipefail
PROJECT_ID="${PROJECT_ID:-meshcore-cloud-gateway}"
REGION="${REGION:-europe-west1}"
gcloud config set project "$PROJECT_ID"
gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com --project="$PROJECT_ID"
echo "Bootstrap complete for $PROJECT_ID ($REGION). Run terraform init and terraform plan from infra/."
