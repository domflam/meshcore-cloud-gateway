#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROJECT_ID="${PROJECT_ID:-meshcore-cloud-gateway}"
REGION="${REGION:-europe-west1}"
TAG="${IMAGE_TAG:-$(git -C "$ROOT" rev-parse --short HEAD)}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/meshcore/ingestion:${TAG}"
cd "$ROOT/infra"
echo "Deploying image: $IMAGE"
echo "Cloud Run stays IAM-protected: allow_public_ingress=false"
terraform init
terraform plan -out=deploy.tfplan \
  -var-file=terraform.tfvars.example \
  -var="container_image=$IMAGE" \
  -var="deploy_service=true" \
  -var="allow_public_ingress=false"
echo "Review plan before approval."
terraform apply deploy.tfplan
rm -f deploy.tfplan
terraform output cloud_run_url
