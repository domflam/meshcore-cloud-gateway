import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from inspect_telemetry import inspect


class InspectTelemetryTests(unittest.TestCase):
    def test_gat562_golden_capture(self):
        result = inspect("0174019b016700d400000000")
        self.assertEqual(result["length_bytes"], 12)
        self.assertEqual(result["data_points"], [
            {"channel": 1, "type": "voltage_v", "value": 4.11},
            {"channel": 1, "type": "temperature_c", "value": 21.2},
        ])
        self.assertEqual(result["unparsed_suffix_hex"], "00000000")

    def test_negative_temperature(self):
        result = inspect("0167ff9c")
        self.assertEqual(result["data_points"][0]["value"], -10.0)

    def test_truncated_record(self):
        result = inspect("017401")
        self.assertEqual(result["data_points"], [])
        self.assertEqual(result["unparsed_suffix_hex"], "017401")

    def test_invalid_hex(self):
        for sample in ("123", "xx", "01:02"):
            with self.subTest(sample=sample):
                with self.assertRaises(ValueError):
                    inspect(sample)


if __name__ == "__main__":
    unittest.main()
