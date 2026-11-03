import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class WifiProvisioningPatchTests(unittest.TestCase):
    def test_preferences_based_wifi_setup(self):
        root = Path(__file__).resolve().parents[1]
        source = '''#include "MyMesh.h"
#include <helpers/MultiSerialInterface.h>
void setup() {
// add wifi interface
#ifdef ENABLE_WIFI_INTERFACE
  if (wifi_enabled && wifi_ssid[0]) {
    WiFi.begin(wifi_ssid, wifi_pwd);
    wifi_interface.begin(TCP_PORT);
    interface_manager.addInterface(InterfaceType::WiFi, &wifi_interface);
  }
#endif
// add usb interface
}
void loop() {
  interface_manager.loop();
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'examples/companion_radio/main.cpp'
            path.parent.mkdir(parents=True)
            path.write_text(source)
            script = root / 'firmware/scripts/enable_wifi_provisioning.py'
            subprocess.run([sys.executable, str(script), tmp], check=True)
            result = path.read_text()
            self.assertNotIn('WiFi.begin(wifi_ssid, wifi_pwd)', result)
            self.assertEqual(result.count('gateway_wifi::begin();'), 1)
            self.assertIn('wifi_interface.begin(TCP_PORT);', result)
            self.assertIn('wifi_enabled = false;', result)
            self.assertLess(result.index('#define GATEWAY_CLOUD_DEFINE_STORAGE'), result.index('#include "MyMesh.h"'))
            self.assertIn('gateway_cloud::loop();', result)
            self.assertIn('void openGatewayCloudSetup()', result)
            original = path.read_text()
            retry = subprocess.run([sys.executable, str(script), tmp], capture_output=True)
            self.assertNotEqual(retry.returncode, 0)
            self.assertEqual(path.read_text(), original)
