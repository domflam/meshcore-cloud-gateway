#!/usr/bin/env bash
# Explicit, opt-in LAB Cloud Run IAM change. No image rebuild or token exposure.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_ID="${PROJECT_ID:-meshcore-cloud-gateway}"
REGION="${REGION:-europe-west1}"
SERVICE="meshcore-ingestion"
cd "$ROOT/infra"
echo "WARNING: this makes $SERVICE publicly invokable at the Cloud Run IAM layer."
echo "The Flask API continues to require its Secret Manager Bearer token for POST /v1/telemetry."
echo "Cloud Run public access can still incur unwanted request volume and cost."
echo "Verify application token validation, billing budgets and monitoring before continuing."
echo
read -r -p "Type ENABLE-LAB-PUBLIC to continue: " answer
[[ "$answer" == "ENABLE-LAB-PUBLIC" ]] || { echo "Cancelled."; exit 1; }
terraform init
# Keep the already deployed image: do not accidentally replace it with a non-existent tag.
IMAGE="$(gcloud run services describe "$SERVICE" --project="$PROJECT_ID" --region="$REGION" --format='value(spec.template.spec.containers[0].image)')"
[[ "$IMAGE" == *"/meshcore/ingestion:"* ]] || { echo "Unexpected Cloud Run image: $IMAGE"; exit 1; }
terraform plan -out=lab-public.tfplan \
  -var-file=terraform.tfvars.example \
  -var="project_id=$PROJECT_ID" \
  -var="region=$REGION" \
  -var="container_image=$IMAGE" \
  -var="deploy_service=true" \
  -var="allow_public_ingress=true"
echo
echo "Review the plan: expect one IAM member allUsers/roles/run.invoker and NO service replacement."
read -r -p "Type APPLY-LAB-PUBLIC to apply this exact plan: " confirm
[[ "$confirm" == "APPLY-LAB-PUBLIC" ]] || { rm -f lab-public.tfplan; echo "Cancelled."; exit 1; }
terraform apply lab-public.tfplan
rm -f lab-public.tfplan
echo "IAM public invoker configured. Application Bearer auth remains mandatory."
