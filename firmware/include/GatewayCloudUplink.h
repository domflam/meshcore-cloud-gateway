#pragma once
// Experimental V0.5 uploader: call enqueue() only after verified telemetry decode.
// HTTPS is deliberately disabled until a safe device authentication path exists.
#include <Arduino.h>
#include <WiFi.h>
#include <Preferences.h>

namespace gateway_cloud {
struct Reading {
  String event_id;
  String node_id;
  String observed_at;
  bool has_voltage = false;\n  bool has_temperature = false;\n  float voltage_v;
  float temperature_c;
};
static constexpr size_t kCapacity = 16;
static Reading queue[kCapacity];
static size_t head = 0, count = 0;
static unsigned long next_attempt_ms = 0;
static uint8_t failures = 0;
static Preferences prefs;
static bool configured = false;
static String endpoint, token;
static bool enabled = false;

static void begin() {
  prefs.begin("gateway-cloud", true);
  endpoint = prefs.getString("url", "");
  token = prefs.getString("token", "");
  enabled = prefs.getBool("enabled", false);
  prefs.end();
  configured = endpoint.startsWith("https://") && token.length() >= 24;
  Serial.printf("[CLOUD] Configured=%s enabled=%s (no secrets logged)\n",
                configured ? "yes" : "no", enabled ? "yes" : "no");
}
static bool enqueue(const Reading &reading) {
  if (!reading.event_id.length() || !reading.node_id.length() ||
      !reading.observed_at.length()) return false;
  if (count == kCapacity) {
    Serial.println("[CLOUD] Queue full: dropping newest reading");
    return false;
  }
  queue[(head + count) % kCapacity] = reading;
  ++count;
  return true;
}
static void loop() {
  if (!enabled || !configured || !count || WiFi.status() != WL_CONNECTED) return;
  if ((int32_t)(millis() - next_attempt_ms) < 0) return;
  // Deliberate fail-closed guard: public Cloud Run access and certificate
  // verification must be designed before enabling transmission.
  // Never use setInsecure() or bypass IAM to make a lab test pass.
  static bool warned = false;
  if (!warned) {
    Serial.println("[CLOUD] Upload held: authenticated endpoint not provisioned");
    warned = true;
  }
}
static size_t pending() { return count; }
} // namespace gateway_cloud
