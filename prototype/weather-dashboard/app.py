"""Read-only weather PWA. Separate service/account from telemetry ingestion."""
import hmac
import os
import re
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request, session, send_from_directory
from google.cloud import bigquery
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
# Cloud Run terminates HTTPS at its trusted proxy; preserve the browser Origin.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=0, x_proto=1, x_host=0, x_port=0, x_prefix=0)
DEMO = os.environ.get('DASHBOARD_DEMO') == '1'
PASSWORD = os.environ.get('DASHBOARD_PASSWORD', '')
SECRET = os.environ.get('SESSION_SECRET', '')
TABLE = os.environ.get('BQ_TABLE', 'meshcore-cloud-gateway.meshcore.telemetry')
NODE = os.environ.get('WEATHER_NODE_ID', 'RAK4631-LAB')
if not re.fullmatch(r'[A-Za-z0-9_-]+\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+', TABLE):
    raise ValueError('Invalid BQ_TABLE')
app.config.update(SECRET_KEY=SECRET or 'local-demo-only', SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SECURE=not DEMO, SESSION_COOKIE_SAMESITE='Strict',
                  PERMANENT_SESSION_LIFETIME=86400, MAX_CONTENT_LENGTH=4096)
_client = None
_cache = None
_cache_at = 0
_lock = threading.Lock()
_attempts = defaultdict(deque)


def ready():
    return DEMO or (len(PASSWORD) >= 16 and len(SECRET) >= 32)


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


def same_origin():
    return request.headers.get('Origin') == request.host_url.rstrip('/')


@app.post('/api/login')
def login():
    if not same_origin():
        return jsonify(error='Origine non autorisée'), 403
    if not ready():
        return jsonify(error='Accès au tableau de bord non configuré'), 503
    if DEMO:
        return jsonify(ok=True)
    # Per-instance LAB throttle; use IAP/edge rate limiting for a wider audience.
    key = request.remote_addr or 'unknown'
    now = time.monotonic()
    with _lock:
        attempts = _attempts[key]
        while attempts and now - attempts[0] > 300:
            attempts.popleft()
        if len(attempts) >= 5:
            return jsonify(error='Patiente quelques minutes avant de réessayer'), 429
        attempts.append(now)
    data = request.get_json(silent=True) or {}
    supplied = data.get('password') if isinstance(data, dict) else None
    if not isinstance(supplied, str) or not hmac.compare_digest(supplied.encode(), PASSWORD.encode()):
        return jsonify(error='Mot de passe incorrect'), 401
    with _lock:
        _attempts.pop(key, None)
    session.clear()
    session['reader'] = True
    session.permanent = True
    return jsonify(ok=True)


@app.post('/api/logout')
def logout():
    if not same_origin():
        return jsonify(error='Origine non autorisée'), 403
    session.clear()
    return jsonify(ok=True)


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
    if not ready():
        return jsonify(error='Accès au tableau de bord non configuré'), 503
    if not DEMO and not session.get('reader'):
        return jsonify(error='Connexion requise'), 401
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
                   fetched_at=datetime.now(timezone.utc).isoformat())


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '8081')))
