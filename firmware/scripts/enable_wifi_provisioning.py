from pathlib import Path
import sys
p = Path(sys.argv[1]) / 'examples/companion_radio/main.cpp'
s = p.read_text()
def patch(a,b):
 global s
 assert s.count(a) == 1, a
 s=s.replace(a,b,1)
patch('#include <helpers/MultiSerialInterface.h>', '#include <helpers/MultiSerialInterface.h>\n#include "GatewayWifiProvisioning.h"')
patch('  WiFi.begin(WIFI_SSID, WIFI_PWD);', '  gateway_wifi::begin();')
patch('  interface_manager.loop();', '  interface_manager.loop();\n  gateway_wifi::loop();')
p.write_text(s)
