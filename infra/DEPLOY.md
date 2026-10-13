# First Cloud Run deployment (V0.4)

Infrastructure baseline has been applied in project `meshcore-cloud-gateway`.

Cloud Run defaults to **IAM-authenticated**, not publicly invokable. Network
ingress is enabled so an authenticated Cloud Shell proxy can reach it. The
application independently checks a Secret Manager bearer token.

Run from Cloud Shell, branch `feature/cloud-ingestion-v04`:

```bash
git pull --ff-only
bash infra/scripts/create-secret-version.sh
bash infra/scripts/build-image.sh
bash infra/scripts/deploy.sh
```

The build uses Cloud Build and pushes an image tagged with the Git commit SHA.
Cloud Build's execution service account needs permission to write to Artifact
Registry. If you receive a permissions error, stop and inspect the build
service account rather than granting project-wide Editor blindly.

The deploy script displays the Terraform plan before apply and enables the
Cloud Run service while keeping public invocation disabled.

## Smoke test

In Cloud Shell terminal 1:

```bash
gcloud run services proxy meshcore-ingestion --project=meshcore-cloud-gateway --region=europe-west1 --port=18080
```

In Cloud Shell terminal 2:

```bash
cd ~/meshcore-cloud-gateway
bash infra/scripts/test-ingestion.sh
```

The proxy uses your gcloud identity to satisfy Cloud Run IAM; the script uses
the Secret Manager token for the Flask application. The current identity must
have Cloud Run Invoker permission. The test sends a unique event ID.

Verify the row (partition filter is mandatory):

```bash
bq query --use_legacy_sql=false 'SELECT event_id,node_id,voltage_v,temperature_c,observed_at FROM `meshcore-cloud-gateway.meshcore.telemetry` WHERE observed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY) ORDER BY observed_at DESC LIMIT 10'
```

Do not set `allow_public_ingress=true` until per-device authentication,
rotation, quotas and abuse protection are ready. Do not print, commit, or paste
the token into chat or logs.
