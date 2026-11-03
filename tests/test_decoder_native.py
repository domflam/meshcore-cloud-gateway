"""Compile the actual portable firmware decoder; no Arduino hardware required."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class DecoderTests(unittest.TestCase):
    def test_native_decoder(self):
        compiler = shutil.which('c++')
        if not compiler:
            self.skipTest('C++ compiler unavailable')
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'test.cpp'
            src.write_text(r'''
#include "TelemetryDecoder.h"
#include <cassert>
#include <cmath>
using namespace cloud_gateway;
int main() {
  uint8_t raw[] = {1,0x74,1,0x9b, 2,0x67,0xff,0x9c, 2,0x68,100,
                   2,0x73,0x27,0x94, 3,2,0,0};
  auto p = rak4631SimulatedWindProfile();
  auto r = decodeTelemetry(raw, sizeof raw, p);
  assert(r.valid && r.parsed_bytes == sizeof raw);
  assert(r.temperature_c == -10 && r.humidity_pct == 50);
  assert(std::fabs(r.pressure_hpa - 1013.2f) < .01f);
  assert(r.has_wind && r.wind_speed_mps == 0 && r.wind_simulated);
  r = decodeTelemetry(raw, sizeof raw);
  assert(r.valid && r.has_voltage && !r.has_wind && !r.has_temperature);
  raw[4] = 9; p.temperature_channel = 9;
  assert(decodeTelemetry(raw, sizeof raw, p).has_temperature);
  for (size_t n : {size_t(1),size_t(3),sizeof(raw)-1})
    assert(!decodeTelemetry(raw,n,p).valid);
  raw[sizeof(raw)-1] = 1;
  assert(!decodeTelemetry(raw,sizeof raw,p).valid);
  p.wind_simulated = false;
  assert(decodeTelemetry(raw,sizeof raw,p).valid);
  uint8_t duplicate[] = {1,0x67,0,1,1,0x67,0,2};
  assert(!decodeTelemetry(duplicate,sizeof duplicate).valid);
  uint8_t legacy[] = {1,0x74,1,0x9b,1,0x67,0,0xd4,0,0,0,0};
  auto old = decodeTelemetry(legacy,sizeof legacy);
  assert(old.valid && old.has_temperature && old.has_voltage);
  assert(!decodeTelemetry(legacy,sizeof legacy,rak4631SimulatedWindProfile()).valid);
  uint8_t unknown[] = {1,0xff,0,0};
  assert(!decodeTelemetry(unknown,sizeof unknown).valid);
  assert(!decodeTelemetry(nullptr,1).valid);
}
'''.replace('#include <cmath>', '#include <cmath>\n#include <initializer_list>'))
            exe = Path(tmp) / 'test'
            subprocess.run([compiler, '-std=c++11', '-Wall', '-Wextra', '-Werror',
                            '-I'+str(root / 'firmware/include'), str(src), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)
