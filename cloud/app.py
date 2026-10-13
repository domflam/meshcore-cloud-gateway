import os
import re
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from google.cloud import bigquery

app = Flask(__name__)
NODE_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
TABLE_ID = os.environ.get("BQ_TABLE", "")
API_TOKEN = os.environ.get("INGEST_TOKEN", "")
_client = None

def client():
    global _client
    if _client is None:
        _client = bigquery.Client()
    return _client

def normalize(payload):
    if not isinstance(payload, dict):
        raise ValueError("JSON object required")
    node_id = payload.get("node_id")
    if not isinstance(node_id, str) or not NODE_RE.fullmatch(node_id):
        raise ValueError("invalid node_id")
    event_id = payload.get("event_id")
    if not isinstance(event_id, str) or not NODE_RE.fullmatch(event_id):
        raise ValueError("invalid event_id")
    ts = payload.get("observed_at")
    if not isinstance(ts, str):
        raise ValueError("observed_at must be ISO 8601")
    try:
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError()
        parsed = parsed.astimezone(timezone.utc)
    except ValueError:
        raise ValueError("invalid observed_at")
    row = {
        "event_id": event_id,
        "node_id": node_id,
        "observed_at": parsed.isoformat(),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "voltage_v": None,
        "temperature_c": None,
        "source": "meshcore",
    }
    if payload.get("source", "meshcore") != "meshcore":
        raise ValueError("unsupported source")
    for field, low, high in (("voltage_v", 0, 30), ("temperature_c", -100, 150)):
        val = payload.get(field)
        if val is not None:
            if isinstance(val, bool) or not isinstance(val, (int, float)) or not low <= val <= high:
                raise ValueError("invalid " + field)
            row[field] = float(val)
    if row["voltage_v"] is None and row["temperature_c"] is None:
        raise ValueError("at least one measurement required")
    return row

@app.get("/health")
def health():
    return jsonify(status="ok")

@app.post("/v1/telemetry")
def ingest():
    if not API_TOKEN or request.headers.get("Authorization") != "Bearer " + API_TOKEN:
        return jsonify(error="unauthorized"), 401
    if not TABLE_ID:
        return jsonify(error="service not configured"), 503
    if not request.is_json:
        return jsonify(error="application/json required"), 415
    try:
        row = normalize(request.get_json())
    except (ValueError, TypeError) as exc:
        return jsonify(error=str(exc)), 400
    errors = client().insert_rows_json(TABLE_ID, [row], row_ids=[row["event_id"]])
    if errors:
        app.logger.error("BigQuery insert failed: %s", errors)
        return jsonify(error="storage unavailable"), 503
    return jsonify(accepted=True, event_id=row["event_id"]), 202
