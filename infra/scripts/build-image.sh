#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROJECT_ID="${PROJECT_ID:-meshcore-cloud-gateway}"
REGION="${REGION:-europe-west1}"
TAG="${IMAGE_TAG:-$(git -C "$ROOT" rev-parse --short HEAD)}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/meshcore/ingestion:${TAG}"
echo "Building ${IMAGE}"
gcloud builds submit "$ROOT/cloud" --tag "$IMAGE" --project "$PROJECT_ID" --region "$REGION"
echo "Image ready: $IMAGE"
echo "For deploy: IMAGE_TAG=$TAG bash infra/scripts/deploy.sh"
