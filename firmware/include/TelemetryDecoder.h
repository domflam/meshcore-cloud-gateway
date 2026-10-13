#pragma once
#include <stddef.h>
#include <stdint.h>

// Bounded CayenneLPP inspection. Unknown record types are left untouched.
namespace cloud_gateway {
struct TelemetryValues {
  bool has_voltage = false;
  bool has_temperature = false;
  float voltage_v = 0;
  float temperature_c = 0;
  size_t parsed_bytes = 0;
};
inline TelemetryValues decodeTelemetry(const uint8_t* bytes, size_t length) {
  TelemetryValues result;
  if (!bytes) return result;
  size_t pos = 0;
  while (pos + 2 <= length) {
    const uint8_t channel = bytes[pos];
    const uint8_t type = bytes[pos + 1];
    if (channel != 1) break; // Other channels not validated yet.
    if (type == 0x74 || type == 0x67) {
      if (pos + 4 > length) break;
      const uint16_t value = (uint16_t(bytes[pos + 2]) << 8) | bytes[pos + 3];
      if (type == 0x74) {
        result.has_voltage = true;
        result.voltage_v = float(value) / 100.0f;
      } else {
        result.has_temperature = true;
        result.temperature_c = float(int16_t(value)) / 10.0f;
      }
      pos += 4;
    } else {
      break; // Do not assume unknown field length.
    }
  }
  result.parsed_bytes = pos;
  return result;
}
} // namespace cloud_gateway
