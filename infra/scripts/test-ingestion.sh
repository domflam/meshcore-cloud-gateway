#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROJECT_ID="${PROJECT_ID:-meshcore-cloud-gateway}"
REGION="${REGION:-europe-west1}"
PORT="${PORT:-18080}"
echo "This test requires 'gcloud run services proxy meshcore-ingestion --project=$PROJECT_ID --region=$REGION --port=$PORT' in another Cloud Shell terminal."
TOKEN="$(gcloud secrets versions access latest --secret=meshcore-ingest-token --project="$PROJECT_ID")"
EVENT_ID="gat562-test-$(date -u +%Y%m%dT%H%M%S)-$$"
BODY="$(python3 -c 'import json,sys,datetime; print(json.dumps({"event_id":sys.argv[1],"node_id":"GAT562-01","observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"voltage_v":4.10,"temperature_c":21.5,"source":"meshcore"}))' "$EVENT_ID")"
curl --fail-with-body --silent --show-error \
  --retry 2 \
  --header "Authorization: Bearer $TOKEN" \
  --header "Content-Type: application/json" \
  --data "$BODY" \
  "http://127.0.0.1:${PORT}/v1/telemetry"
echo
echo "Submitted event_id: $EVENT_ID"
