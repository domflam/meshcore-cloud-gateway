#pragma once
#include <stddef.h>
#include <stdint.h>

namespace cloud_gateway {
// Trusted per-node configuration; -1 disables a measurement. Legacy default.
struct TelemetryProfile {
  int voltage_channel = 1, temperature_channel = 1;
  int humidity_channel = -1, pressure_channel = -1, wind_channel = -1;
  bool wind_simulated = false;
  size_t trailing_zero_padding_bytes = 4; // Validated historical GAT562 capture only.
};
inline TelemetryProfile rak4631SimulatedWindProfile() {
  TelemetryProfile p;
  p.temperature_channel = p.humidity_channel = p.pressure_channel = 2;
  p.wind_channel = 3;
  p.wind_simulated = true;
  p.trailing_zero_padding_bytes = 0;
  return p;
}
struct TelemetryValues {
  bool has_voltage = false, has_temperature = false, has_humidity = false;
  bool has_pressure = false, has_wind = false, wind_simulated = false;
  bool valid = true;
  float voltage_v = 0, temperature_c = 0, humidity_pct = 0;
  float pressure_hpa = 0, wind_speed_mps = 0;
  size_t parsed_bytes = 0;
};
inline TelemetryValues decodeTelemetry(const uint8_t* bytes, size_t length,
                                      const TelemetryProfile& profile = TelemetryProfile()) {
  TelemetryValues r;
  if (!bytes) { r.valid = length == 0; return r; }
  size_t pos = 0;
  while (pos + 2 <= length) {
    // An explicit legacy framing allowance, never a generic unknown-type skip.
    if (profile.trailing_zero_padding_bytes &&
        length - pos == profile.trailing_zero_padding_bytes) {
      bool zeros = true;
      for (size_t i = pos; i < length; ++i) zeros = zeros && bytes[i] == 0;
      if (zeros) { pos = length; break; }
    }
    const uint8_t channel = bytes[pos], type = bytes[pos + 1];
    size_t size;
    switch (type) {
      case 0x68: case 0x78: size = 1; break;
      case 0x02: case 0x67: case 0x73: case 0x74: size = 2; break;
      default: r.valid = false; r.parsed_bytes = pos; return r;
    }
    if (pos + 2 + size > length) break;
    const uint16_t raw = size == 1 ? bytes[pos + 2] :
        (uint16_t(bytes[pos + 2]) << 8) | bytes[pos + 3];
    const int signed_raw = raw >= 32768 ? int(raw) - 65536 : int(raw);
    bool* present = nullptr;
    float* value = nullptr;
    float decoded = 0, low = 0, high = 0;
    if (type == 0x74 && channel == profile.voltage_channel) {
      present = &r.has_voltage; value = &r.voltage_v;
      decoded = raw / 100.0f; high = 30;
    } else if (type == 0x67 && channel == profile.temperature_channel) {
      present = &r.has_temperature; value = &r.temperature_c;
      decoded = signed_raw / 10.0f; low = -100; high = 150;
    } else if (type == 0x68 && channel == profile.humidity_channel) {
      present = &r.has_humidity; value = &r.humidity_pct;
      decoded = raw / 2.0f; high = 100;
    } else if (type == 0x73 && channel == profile.pressure_channel) {
      present = &r.has_pressure; value = &r.pressure_hpa;
      decoded = raw / 10.0f; high = 2000;
    } else if (type == 0x02 && channel == profile.wind_channel) {
      present = &r.has_wind; value = &r.wind_speed_mps;
      decoded = signed_raw / 100.0f; high = 100;
      r.wind_simulated = profile.wind_simulated;
      if (r.wind_simulated && raw != 0) r.valid = false;
    }
    if (present) {
      if (*present || decoded < low || decoded > high) r.valid = false;
      *present = true; *value = decoded;
    }
    pos += 2 + size;
  }
  r.parsed_bytes = pos;
  if (pos != length) r.valid = false;
  return r;
}
} // namespace cloud_gateway
