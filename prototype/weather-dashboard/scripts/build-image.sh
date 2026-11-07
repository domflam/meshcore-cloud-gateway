#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_ID=meshcore-cloud-gateway
REGION=europe-west1
TAG="$(git -C "$ROOT" rev-parse --short HEAD)"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/meshcore/weather-dashboard:${TAG}"
gcloud builds submit "$ROOT" --tag "$IMAGE" --project="$PROJECT_ID" --region="$REGION"
echo "Image ready: $IMAGE"
