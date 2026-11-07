"""Read-only weather PWA. Separate service/account from telemetry ingestion."""
import os
import re
import threading
import time
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request, send_from_directory
from google.cloud import bigquery
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
# Cloud Run terminates HTTPS at its trusted proxy; preserve the browser Origin.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=0, x_proto=1, x_host=0, x_port=0, x_prefix=0)
DEMO = os.environ.get('DASHBOARD_DEMO') == '1'
TABLE = os.environ.get('BQ_TABLE', 'meshcore-cloud-gateway.meshcore.telemetry')
NODE = os.environ.get('WEATHER_NODE_ID', 'RAK4631-LAB')
STALE_AFTER_MINUTES = int(os.environ.get('WEATHER_STALE_AFTER_MINUTES', '30'))
if not 1 <= STALE_AFTER_MINUTES <= 1440:
    raise ValueError('WEATHER_STALE_AFTER_MINUTES must be 1..1440')
if not re.fullmatch(r'[A-Za-z0-9_-]+\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+', TABLE):
    raise ValueError('Invalid BQ_TABLE')
app.config.update(MAX_CONTENT_LENGTH=4096)
_client = None
_cache = None
_cache_at = 0
_lock = threading.Lock()
@app.after_request
def headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.get('/')
def home():
    return render_template('index.html')


@app.get('/manifest.webmanifest')
def manifest():
    return send_from_directory('static', 'manifest.webmanifest', mimetype='application/manifest+json')


@app.get('/sw.js')
def service_worker():
    response = send_from_directory('static', 'sw.js', mimetype='application/javascript')
    response.headers['Cache-Control'] = 'no-cache'
    return response


@app.get('/health')
def health():
    return jsonify(status='ok')


def read_weather():
    global _client, _cache, _cache_at
    with _lock:
        if _cache is not None and time.monotonic() - _cache_at < 60:
            return _cache
        if _client is None:
            _client = bigquery.Client()
        sql = f'''SELECT event_id, node_id, observed_at, voltage_v, temperature_c,
                         humidity_pct, pressure_hpa, wind_speed_mps, wind_simulated
                  FROM `{TABLE}`
                  WHERE observed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
                    AND observed_at <= CURRENT_TIMESTAMP()
                    AND node_id = @node
                  QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY received_at DESC) = 1
                  ORDER BY observed_at DESC LIMIT 300'''
        config = bigquery.QueryJobConfig(maximum_bytes_billed=100_000_000,
                  query_parameters=[bigquery.ScalarQueryParameter('node', 'STRING', NODE)])
        result = _client.query(sql, job_config=config, timeout=10).result(timeout=15)
        points = []
        for row in result:
            point = dict(row)
            point['observed_at'] = row['observed_at'].astimezone(timezone.utc).isoformat()
            points.append(point)
        _cache = points
        _cache_at = time.monotonic()
        return points


@app.get('/api/weather')
def weather():
    if DEMO:
        points = [dict(event_id=f'capture-{i}', node_id=NODE, observed_at=stamp,
                       voltage_v=4.08, temperature_c=temp, humidity_pct=humidity,
                       pressure_hpa=pressure, wind_speed_mps=0, wind_simulated=True)
                  for i, stamp, temp, humidity, pressure in (
                      (2, '2026-11-03T13:18:48+00:00', 20.1, 60, 1016.6),
                      (1, '2026-11-03T13:17:46+00:00', 20, 59, 1016.7))]
    else:
        try:
            points = read_weather()
        except Exception:
            app.logger.exception('Weather read failed')
            return jsonify(error='Lecture des mesures indisponible. Réessaie dans un instant.'), 503
    return jsonify(mode='demo' if DEMO else 'live', node_id=NODE,
                   latest=points[0] if points else None, history=list(reversed(points)),
                   stale_after_minutes=STALE_AFTER_MINUTES,
                   fetched_at=datetime.now(timezone.utc).isoformat())


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '8081')))
