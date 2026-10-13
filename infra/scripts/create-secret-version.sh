#!/usr/bin/env bash
set -euo pipefail
PROJECT_ID="${PROJECT_ID:-meshcore-cloud-gateway}"
SECRET_ID="meshcore-ingest-token"
echo "Generating a random 32-byte ingestion token and adding a Secret Manager version."
echo "The token will not be printed or written to the repository."
python3 -c 'import secrets,sys; sys.stdout.write(secrets.token_urlsafe(32))' | \
  gcloud secrets versions add "$SECRET_ID" --data-file=- --project="$PROJECT_ID"
echo "Token created. Retrieve it only in a trusted shell when testing."
