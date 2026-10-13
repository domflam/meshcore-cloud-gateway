# V0.4 — Cloud ingestion prototype

This is an independent prototype. It is **not deployed** and the Heltec firmware
does **not** send HTTP requests yet.

## Contract

POST /v1/telemetry with JSON and Authorization: Bearer <token>.

Example body: [sample-telemetry.json](sample-telemetry.json).
Response: HTTP 202 for a successful BigQuery streaming insert.
GET /health returns 200 without authentication (liveness only).

Fields: event_id (stable per measurement, required), node_id (required),
observed_at (ISO-8601 UTC/offset, required), voltage_v (optional),
temperature_c (optional), source (must be meshcore). At least one measurement
must be present. Keep event_id stable across retries.

## Local test

```sh
cd cloud
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## GCP preparation (manual; no deployment has been performed)

1. Choose a GCP project and billing account, enable Cloud Run, Cloud Build,
   Artifact Registry, BigQuery and Secret Manager APIs.
2. Replace PROJECT_ID and DATASET_ID in bigquery.sql and run it in the chosen
   BigQuery location (europe-west1 in this example).
3. Create a dedicated Cloud Run service account with BigQuery Data Editor
   scoped to the dataset, and BigQuery Job User only if needed.
4. Store a random ingestion token in Secret Manager. Never commit it to Git.
5. Build and deploy the container to Cloud Run in europe-west1, using
   BQ_TABLE=PROJECT_ID.DATASET_ID.telemetry and INGEST_TOKEN supplied from
   Secret Manager. Configure the runtime service account.
6. Restrict Cloud Run ingress and authentication appropriately before
   production. The prototype bearer-token approach assumes HTTPS and a
   deliberately public endpoint; do not deploy publicly until rate limits,
   credential rotation, replay protection and abuse controls are designed.

BigQuery streaming insertId deduplication is **best effort**, not guaranteed.
For analytics, query a deduplicated view using event_id or implement stronger
idempotency in the next iteration.

The gateway must not embed an API token in a public repository or published
binary without accepting the extraction risk. Plan per-device credentials
and rotation before physical deployment.
