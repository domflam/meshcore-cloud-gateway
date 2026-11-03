import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['INGEST_TOKEN'] = 'test-token'
os.environ['BQ_TABLE'] = 'project.dataset.telemetry'
from app import normalize, app
from telemetry import from_mqtt
from mqtt_bridge import forward

META = dict(node_id='RAK4631-LAB', event_id='rak-001', observed_at='2026-11-03T12:00:00Z')
HEX = '0174019b0267ff9c0268640273279403020000'
PROFILES = json.loads((Path(__file__).resolve().parents[1] / 'profiles.example.json').read_text())


class EnvironmentalTests(unittest.TestCase):
    def test_raw_rak_to_api_to_bigquery(self):
        row = from_mqtt(dict(META, lpp_hex=HEX), PROFILES)
        for field, value in dict(voltage_v=4.11, temperature_c=-10,
                                 humidity_pct=50, pressure_hpa=1013.2,
                                 wind_speed_mps=0, wind_simulated=True).items():
            self.assertEqual(row[field], value)
        with patch('app.client') as storage:
            storage.return_value.insert_rows_json.return_value = []
            response = app.test_client().post('/v1/telemetry', json=row,
                       headers={'Authorization': 'Bearer test-token'})
            self.assertEqual(response.status_code, 202)
            inserted = storage.return_value.insert_rows_json.call_args
            self.assertEqual(inserted.args[1][0]['wind_simulated'], True)
            self.assertEqual(inserted.kwargs['row_ids'], ['rak-001'])

    def test_actual_rak_capture(self):
        raw = '01740198026700c7026876027327b70279ffe303020000016700e600'
        row = from_mqtt(dict(META, lpp_hex=raw), PROFILES)
        self.assertEqual(row['temperature_c'], 19.9)
        self.assertEqual(row['humidity_pct'], 59)
        self.assertEqual(row['pressure_hpa'], 1016.7)
        self.assertEqual(row['wind_speed_mps'], 0)
        self.assertIs(row['wind_simulated'], True)
        for invalid in (raw[:-2]+'01', raw+'00', raw.replace('0279ffe3', '02ffffe3')):
            with self.subTest(raw=invalid), self.assertRaises(ValueError):
                from_mqtt(dict(META, lpp_hex=invalid), PROFILES)

    def test_channels_are_per_node(self):
        profiles = {'other': {'9:temperature_c': {'field': 'temperature_c'},
                              '8:analog_input': {'field': 'wind_speed_mps', 'simulated': False}}}
        row = from_mqtt(dict(META, node_id='other', lpp_hex='096700c808020000'), profiles)
        self.assertEqual(row['temperature_c'], 20)
        self.assertIs(row['wind_simulated'], False)

    def test_legacy_and_zero(self):
        self.assertEqual(normalize(dict(META, voltage_v=0))['voltage_v'], 0)
        row = from_mqtt(dict(META, wind_speed_mps=0), {})
        self.assertIsNone(row['wind_simulated'])
        self.assertEqual(from_mqtt(dict(META, node_id='GAT562-01',
                         lpp_hex='0174019b016700d400000000'), PROFILES)['temperature_c'], 21.2)

    def test_bad_measurements(self):
        for field, values in {'humidity_pct': [-1, 101], 'pressure_hpa': [-1, 2001],
                              'wind_speed_mps': [-1, 101], 'temperature_c': [-101, 151],
                              'voltage_v': [-1, 31]}.items():
            for value in values + [True, '0', float('nan'), float('inf'), -float('inf')]:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    normalize(dict(META, **{field: value}))
        for fields in ({}, {'wind_simulated': True}, {'wind_speed_mps': 1, 'wind_simulated': True},
                       {'wind_speed_mps': 0, 'wind_simulated': 1}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                normalize(dict(META, **fields))

    def test_bad_raw(self):
        for raw in [HEX[:-2], HEX+'ff', HEX+'00ff', HEX+'02670001',
                    HEX.replace('03020000', '03020001'), '03020000', 'xx', '0']:
            with self.subTest(raw=raw):
                # Wind-only zero is a legitimate measurement.
                if raw == '03020000':
                    self.assertEqual(from_mqtt(dict(META, lpp_hex=raw), PROFILES)['wind_speed_mps'], 0)
                else:
                    with self.assertRaises(ValueError):
                        from_mqtt(dict(META, lpp_hex=raw), PROFILES)
        with self.assertRaises(ValueError):
            from_mqtt(dict(META, node_id='unknown', lpp_hex=HEX), PROFILES)
        with self.assertRaises(ValueError):
            from_mqtt(dict(META, temperature_c=1, lpp_hex=HEX), PROFILES)

    @patch('mqtt_bridge.urllib.request.urlopen')
    def test_optional_mqtt_forward_acknowledgement(self, urlopen):
        response = MagicMock(status=202)
        urlopen.return_value.__enter__.return_value = response
        forward(json.dumps(dict(META, lpp_hex=HEX)), PROFILES, 'https://example.test/v1/telemetry', 'test')
        req = urlopen.call_args.args[0]
        self.assertEqual(json.loads(req.data)['event_id'], META['event_id'])
        response.status = 503
        with self.assertRaises(RuntimeError):
            forward(json.dumps(dict(META, lpp_hex=HEX)), PROFILES, 'https://example.test/v1/telemetry', 'test')
