#!/usr/bin/env bash
# Idempotent LAB preparation. Does not deploy or modify meshcore-ingestion.
set -euo pipefail
PROJECT_ID=meshcore-cloud-gateway
REGION=europe-west1
SA="weather-dashboard@${PROJECT_ID}.iam.gserviceaccount.com"
for tool in gcloud bq python3; do command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 1; }; done
if ! gcloud iam service-accounts describe "$SA" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam service-accounts create weather-dashboard --display-name="Weather dashboard read only" --project="$PROJECT_ID"
fi
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SA" --role=roles/bigquery.jobUser --condition=None >/dev/null
bq --project_id="$PROJECT_ID" add-iam-policy-binding --member="serviceAccount:$SA" --role=roles/bigquery.dataViewer "${PROJECT_ID}:meshcore.telemetry" >/dev/null
echo "Ready: dedicated account and read-only table access. No secrets required; no deployment performed."
