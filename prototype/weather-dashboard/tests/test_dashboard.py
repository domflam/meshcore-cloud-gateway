import importlib.util
import json
import struct
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('weather_dashboard_app', ROOT / 'app.py')
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.demo = module.DEMO
        module.DEMO = False
        module.PASSWORD = 'test-dashboard-password'
        module.SECRET = 'test-session-secret-with-at-least-32-characters'
        module.app.config.update(TESTING=True, SECRET_KEY=module.SECRET)
        module._attempts.clear()
        module._cache = None
        module._client = None
        self.client = module.app.test_client()

    def tearDown(self):
        module.DEMO = self.demo

    def login(self):
        return self.client.post('/api/login', json={'password': module.PASSWORD},
                               base_url='https://localhost', headers={'Origin': 'https://localhost'})

    def test_private_and_fail_closed(self):
        self.assertEqual(self.client.get('/api/weather').status_code, 401)
        module.SECRET = ''
        self.assertEqual(self.client.get('/api/weather').status_code, 503)

    def test_login_cookie_origin_and_logout(self):
        response = self.client.post('/api/login', json={'password': module.PASSWORD}, base_url='https://localhost')
        self.assertEqual(response.status_code, 403)
        response = self.login()
        self.assertEqual(response.status_code, 200)
        cookie = response.headers['Set-Cookie']
        for flag in ('HttpOnly', 'Secure', 'SameSite=Strict'):
            self.assertIn(flag, cookie)
        with patch.object(module, 'read_weather', return_value=[]):
            result = self.client.get('/api/weather', base_url='https://localhost')
            self.assertEqual(result.status_code, 200)
            self.assertIsNone(result.json['latest'])
        self.client.post('/api/logout', base_url='https://localhost', headers={'Origin': 'https://localhost'})
        self.assertEqual(self.client.get('/api/weather', base_url='https://localhost').status_code, 401)

    def test_cloud_run_https_proxy_origin(self):
        response = self.client.post('/api/login', json={'password': module.PASSWORD},
                   base_url='http://weather.example.test',
                   headers={'Origin': 'https://weather.example.test', 'X-Forwarded-Proto': 'https'})
        self.assertEqual(response.status_code, 200)

    def test_bad_password_and_throttling(self):
        for _ in range(5):
            response = self.client.post('/api/login', json={'password': 'wrong'},
                       base_url='https://localhost', headers={'Origin': 'https://localhost'})
            self.assertEqual(response.status_code, 401)
        self.assertEqual(self.login().status_code, 429)

    def test_demo_has_explicit_mode_and_capture_dates(self):
        module.DEMO = True
        with patch.object(module.bigquery, 'Client') as client:
            response = self.client.get('/api/weather')
            client.assert_not_called()
        data = response.json
        self.assertEqual(data['mode'], 'demo')
        self.assertEqual(data['latest']['temperature_c'], 20.1)
        self.assertEqual(data['latest']['wind_speed_mps'], 0)
        self.assertIs(data['latest']['wind_simulated'], True)
        self.assertTrue(data['latest']['observed_at'].startswith('2026-11-03T13:18:48'))
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_query_is_bounded_per_node_deduplicated_and_cached(self):
        row = dict(node_id='RAK4631-LAB', event_id='1', observed_at=datetime.now(timezone.utc),
                   voltage_v=None, temperature_c=None, humidity_pct=0,
                   pressure_hpa=1000, wind_speed_mps=0, wind_simulated=False)
        client = MagicMock()
        client.query.return_value.result.return_value = [row]
        module._client = client
        self.login()
        first = self.client.get('/api/weather', base_url='https://localhost')
        self.assertEqual(first.status_code, 200)
        self.assertIsNone(first.json['latest']['temperature_c'])
        self.assertIs(first.json['latest']['wind_simulated'], False)
        self.client.get('/api/weather', base_url='https://localhost')
        self.assertEqual(client.query.call_count, 1)
        sql = client.query.call_args.args[0]
        self.assertIn('INTERVAL 24 HOUR', sql)
        self.assertIn('node_id = @node', sql)
        self.assertIn('PARTITION BY event_id', sql)
        config = client.query.call_args.kwargs['job_config']
        self.assertEqual(config.maximum_bytes_billed, 100_000_000)
        self.assertEqual(config.query_parameters[0].value, 'RAK4631-LAB')

    def test_storage_error_is_sanitized(self):
        self.login()
        with patch.object(module, 'read_weather', side_effect=RuntimeError('private error detail')):
            response = self.client.get('/api/weather', base_url='https://localhost')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('private error detail', response.get_data(as_text=True))

    def test_installable_assets_and_security_headers(self):
        manifest = self.client.get('/manifest.webmanifest')
        data = json.loads(manifest.data)
        self.assertEqual(data['display'], 'standalone')
        self.assertEqual(data['start_url'], '/')
        for icon in data['icons']:
            result = self.client.get(icon['src'])
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.data[:8], b'\x89PNG\r\n\x1a\n')
            width, height = struct.unpack('!II', result.data[16:24])
            self.assertEqual(icon['sizes'], f'{width}x{height}')
            result.close()
        home = self.client.get('/')
        self.assertIn("default-src 'self'", home.headers['Content-Security-Policy'])
        manifest.close()
        with self.client.get('/sw.js') as sw:
            self.assertEqual(sw.headers['Cache-Control'], 'no-cache')
