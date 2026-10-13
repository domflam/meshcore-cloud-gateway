import os
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template
from google.cloud import bigquery

app = Flask(__name__)
client = bigquery.Client()
TABLE = os.getenv("BQ_TABLE", "meshcore-cloud-gateway.meshcore.telemetry")

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/api/weather")
def weather():
    # Table name comes from deployment configuration, never from user input.
    sql = f"""
        SELECT node_id, observed_at, voltage_v, temperature_c
        FROM `{TABLE}`
        WHERE observed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
        ORDER BY observed_at DESC
        LIMIT 300
    """
    rows = list(client.query(sql, job_config=bigquery.QueryJobConfig(maximum_bytes_billed=100_000_000)).result())
    points = [{"node": r.node_id, "time": r.observed_at.isoformat() if hasattr(r.observed_at, "isoformat") else str(r.observed_at), "voltage": r.voltage_v, "temperature": r.temperature_c} for r in rows]
    return jsonify({"latest": points[0] if points else None, "history": list(reversed(points))})

@app.get("/health")
def health():
    return jsonify(status="ok")
