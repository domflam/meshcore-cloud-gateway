import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class LabPatchTests(unittest.TestCase):
    def test_profile_bound_to_target_and_legacy_default(self):
        root = Path(__file__).resolve().parents[1]
        for options, node, profile in [([], 'GAT562-01', 'TelemetryProfile profile'),
            (['--node-id', 'RAK4631-LAB', '--public-key', '11'*32,
              '--profile', 'rak-simulated', '--temperature-channel', '9'],
             'RAK4631-LAB', 'rak4631SimulatedWindProfile()')]:
            with self.subTest(node=node), tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / 'examples/companion_radio'
                target.mkdir(parents=True)
                for filename in ('MyMesh.cpp', 'MyMesh.h'):
                    shutil.copy(root / 'examples/companion_radio' / filename, target)
                subprocess.run([sys.executable, str(root / 'firmware/scripts/apply_lab_patch.py'),
                                tmp, *options], check=True, capture_output=True)
                cpp = (target / 'MyMesh.cpp').read_text()
                self.assertIn('reading.node_id = "'+node+'"', cpp)
                self.assertIn(profile, cpp)
                self.assertIn('len - 4, profile)', cpp)
                self.assertIn('reading.wind_simulated = decoded.wind_simulated;', cpp)
                if options:
                    self.assertIn('profile.temperature_channel = 9;', cpp)
                    self.assertIn('0x11,0x11,0x11', cpp)
                retry = subprocess.run([sys.executable, str(root / 'firmware/scripts/apply_lab_patch.py'), tmp], capture_output=True)
                self.assertNotEqual(retry.returncode, 0)
