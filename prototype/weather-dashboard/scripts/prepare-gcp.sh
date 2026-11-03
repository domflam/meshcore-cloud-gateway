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
for secret_id in weather-dashboard-password weather-dashboard-session; do
  if ! gcloud secrets describe "$secret_id" --project="$PROJECT_ID" >/dev/null 2>&1; then
    gcloud secrets create "$secret_id" --replication-policy=automatic --project="$PROJECT_ID"
    python3 -c 'import secrets,sys; sys.stdout.write(secrets.token_urlsafe(32))' |
      gcloud secrets versions add "$secret_id" --data-file=- --project="$PROJECT_ID"
  fi
  if [[ "$(gcloud secrets versions describe latest --secret="$secret_id" --project="$PROJECT_ID" --format='value(state)')" != ENABLED ]]; then
    echo "Secret $secret_id has no enabled latest version; inspect it before continuing." >&2
    exit 1
  fi
  gcloud secrets add-iam-policy-binding "$secret_id" --member="serviceAccount:$SA" --role=roles/secretmanager.secretAccessor --condition=None --project="$PROJECT_ID" >/dev/null
done
echo "Ready: dedicated account, read-only table access, two dedicated secrets. No deployment performed."
