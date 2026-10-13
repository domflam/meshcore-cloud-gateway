import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from inspect_telemetry import inspect


class InspectTelemetryTests(unittest.TestCase):
    def test_gat562_golden_capture(self):
        result = inspect("0174019b016700d400000000")
        self.assertEqual(result["length_bytes"], 12)
        self.assertEqual(result["hex"], "0174019b016700d400000000")
        self.assertEqual(len(result["octets"]), 12)
        self.assertEqual(result["uint16_be_candidates"], [372, 411, 359, 212, 0, 0])
        self.assertIn("unknown", result["interpretation"])

    def test_invalid_hex(self):
        for sample in ("123", "xx", "01:02"):
            with self.subTest(sample=sample):
                with self.assertRaises(ValueError):
                    inspect(sample)


if __name__ == "__main__":
    unittest.main()
