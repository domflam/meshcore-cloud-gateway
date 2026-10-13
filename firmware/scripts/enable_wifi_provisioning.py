from pathlib import Path
import sys
p = Path(sys.argv[1]) / 'examples/companion_radio/main.cpp'
s = p.read_text()
def patch(a,b):
 global s
 assert s.count(a) == 1, a
 s=s.replace(a,b,1)
patch('#include <helpers/MultiSerialInterface.h>', '#include <helpers/MultiSerialInterface.h>\n#include "GatewayWifiProvisioning.h"')
patch('  WiFi.begin(WIFI_SSID, WIFI_PWD);', '  gateway_wifi::begin();\n#ifdef CLOUD_GATEWAY_LAB_UPLINK\n  gateway_cloud::begin();\n#endif')
patch('  interface_manager.loop();', '  interface_manager.loop();\n  gateway_wifi::loop();\n#ifdef CLOUD_GATEWAY_LAB_UPLINK\n  gateway_cloud::loop();\n#endif')
s += """\n#ifdef CLOUD_GATEWAY_LAB_UPLINK\nvoid openGatewayCloudSetup() { gateway_wifi::openSetupPortal(); }\n#endif\n"""\np.write_text(s)\n