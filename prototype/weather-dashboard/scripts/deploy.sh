#!/usr/bin/env bash
# Deploys only the approved PWA service. Do not use for ingestion.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="$(git -C "$ROOT" rev-parse --short HEAD)"
PROJECT_ID=meshcore-cloud-gateway
REGION=europe-west1
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/meshcore/weather-dashboard:${TAG}"
echo "Deploying meshcore-weather-dashboard (separate from meshcore-ingestion)."
echo "Public HTTPS login page; measurements require the dedicated dashboard password."
gcloud run deploy meshcore-weather-dashboard \
  --project="$PROJECT_ID" --region="$REGION" \
  --image="$IMAGE" \
  --service-account="weather-dashboard@${PROJECT_ID}.iam.gserviceaccount.com" \
  --allow-unauthenticated \
  --min-instances=0 --max-instances=1 \
  --memory=256Mi --cpu=1 --timeout=30 --concurrency=8 \
  --set-env-vars="BQ_TABLE=${PROJECT_ID}.meshcore.telemetry,WEATHER_NODE_ID=RAK4631-LAB" \
  --set-secrets="DASHBOARD_PASSWORD=weather-dashboard-password:latest,SESSION_SECRET=weather-dashboard-session:latest"
gcloud run services describe meshcore-weather-dashboard --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)'
