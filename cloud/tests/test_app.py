import os
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["INGEST_TOKEN"] = "test-token"
os.environ["BQ_TABLE"] = "project.dataset.telemetry"
from app import app, normalize

SAMPLE = {
    "event_id": "gat562-20261013-001",
    "node_id": "GAT562-01",
    "observed_at": "2026-10-13T12:00:00Z",
    "voltage_v": 4.10,
    "temperature_c": 21.5,
}

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_normalize(self):
        self.assertEqual(normalize(SAMPLE)["voltage_v"], 4.10)

    def test_invalid_timestamp(self):
        with self.assertRaises(ValueError):
            normalize({**SAMPLE, "observed_at": "yesterday"})

    def test_requires_token(self):
        response = self.client.post("/v1/telemetry", json=SAMPLE)
        self.assertEqual(response.status_code, 401)

    @patch("app.client")
    def test_accepts_measurement(self, mocked_client):
        mocked_client.return_value.insert_rows_json.return_value = []
        response = self.client.post("/v1/telemetry", json=SAMPLE, headers={"Authorization": "Bearer test-token"})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(mocked_client.return_value.insert_rows_json.call_args.kwargs["row_ids"], [SAMPLE["event_id"]])

if __name__ == "__main__":
    unittest.main()
