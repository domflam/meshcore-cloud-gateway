# Infrastructure as Code — MeshCore Cloud Gateway

Project: `meshcore-cloud-gateway`; region: `europe-west1`.

Terraform provisions APIs, Artifact Registry, BigQuery dataset/table, a dedicated
Cloud Run runtime service account, dataset-scoped write permission and a Secret
Manager secret **without** a secret version. Cloud Run is disabled by default.

## Bootstrap

Cloud Shell prerequisites: project billing linked, permission to enable APIs,
Terraform installed, and authenticated gcloud account.

```sh
git clone https://github.com/domflam/meshcore-cloud-gateway.git
cd meshcore-cloud-gateway
git checkout feature/cloud-ingestion-v04
bash infra/scripts/bootstrap.sh
bash infra/scripts/plan.sh
```

Review the plan before applying:

```sh
cd infra
terraform apply -var-file=terraform.tfvars.example
```

If you already created the dataset manually, **import** it into Terraform state
before applying: `terraform import google_bigquery_dataset.telemetry projects/meshcore-cloud-gateway/datasets/meshcore`.
Do not create the same resource twice.

## Deploy later

Build and push the image to Artifact Registry, add a secret version through
Secret Manager without putting its value in Terraform or Git, then set
`deploy_service=true` and the image URI. The default Cloud Run service is
internal-only. For a remote Wi-Fi gateway, public ingress requires an explicit
opt-in (`allow_public_ingress=true`) and security review of token handling,
rotation, replay protection, quotas and abuse prevention.

**Do not commit Terraform state**: it may contain sensitive metadata.
This prototype uses local state; configure a versioned, access-controlled GCS
backend before team or production use. Do not use Terraform destroy on the
telemetry dataset; the table is protected.

Cost: billing and usage are not capped by Terraform. Configure a billing budget
and alerts in the GCP console separately.
