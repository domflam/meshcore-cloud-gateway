from pathlib import Path
import sys
p = Path(sys.argv[1]) / 'examples/companion_radio/main.cpp'
s = p.read_text()
def patch(a,b):
 global s
 assert s.count(a) == 1, a
 s=s.replace(a,b,1)
patch('#include "MyMesh.h"', '#ifdef CLOUD_GATEWAY_LAB_UPLINK\n#define GATEWAY_CLOUD_DEFINE_STORAGE\n#endif\n#include "MyMesh.h"')
patch('#include <helpers/MultiSerialInterface.h>', '#include <helpers/MultiSerialInterface.h>\n#include "GatewayWifiProvisioning.h"')
if '  WiFi.begin(WIFI_SSID, WIFI_PWD);' in s:
 patch('  WiFi.begin(WIFI_SSID, WIFI_PWD);', '  gateway_wifi::begin();\n#ifdef CLOUD_GATEWAY_LAB_UPLINK\n  gateway_cloud::begin();\n#endif')
else:
 start = '// add wifi interface\n#ifdef ENABLE_WIFI_INTERFACE'
 end = '// add usb interface'
 assert s.count(start) == 1 and s.count(end) == 1
 before, rest = s.split(start, 1)
 old_setup, after = rest.split(end, 1)
 assert 'WiFi.begin(wifi_ssid, wifi_pwd);' in old_setup
 # LAB NVS provisioning owns credentials/reconnects; bypass upstream defaults.
 s = before + start + """
  board.setInhibitSleep(true);
  gateway_wifi::begin();
#ifdef CLOUD_GATEWAY_LAB_UPLINK
  gateway_cloud::begin();
#endif
  wifi_enabled = false; // disable upstream reconnect loop using its separate prefs
  wifi_interface.begin(TCP_PORT);
  interface_manager.addInterface(InterfaceType::WiFi, &wifi_interface);
#endif

""" + end + after
patch('  interface_manager.loop();', '  interface_manager.loop();\n  gateway_wifi::loop();\n#ifdef CLOUD_GATEWAY_LAB_UPLINK\n  gateway_cloud::loop();\n#endif')
s += """
#ifdef CLOUD_GATEWAY_LAB_UPLINK
void openGatewayCloudSetup() { gateway_wifi::openSetupPortal(); }
#endif
"""
p.write_text(s)
