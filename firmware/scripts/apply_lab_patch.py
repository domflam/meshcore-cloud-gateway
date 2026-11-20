#!/usr/bin/env python3
"""Apply minimal LAB-only BLE telemetry poller to a checked-out MeshCore source tree.

Fails closed if expected upstream anchors have changed.
"""
from pathlib import Path
import argparse
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("root", type=Path)
parser.add_argument("--node-id", default="GAT562-01")
parser.add_argument("--public-key")
parser.add_argument("--profile", choices=("legacy", "rak-simulated", "rak-real"), default="legacy")
for measurement in ("voltage", "temperature", "humidity", "pressure", "wind"):
    parser.add_argument("--" + measurement + "-channel", type=int)
args = parser.parse_args()
if args.public_key is None:
    if args.profile != "legacy" or args.node_id != "GAT562-01":
        parser.error("a custom node/profile requires an explicit public key")
    args.public_key = "26b5986ec521b62b9811688513f9a720b5245cd9448f90d4cbe3e0ca23c817ca"
if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", args.node_id):
    parser.error("invalid node id")
if not re.fullmatch(r"[0-9a-fA-F]{64}", args.public_key):
    parser.error("public key must be 32 bytes of hex")
root = args.root
cpp = root / "examples/companion_radio/MyMesh.cpp"
hdr = root / "examples/companion_radio/MyMesh.h"
source, header = cpp.read_text(), hdr.read_text()

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

header = replace_once(header, '#include "DataStore.h"', '''#include "DataStore.h"
#ifdef CLOUD_GATEWAY_LAB_POLL
#include "TelemetryScheduler.h"
#include "GatewayStations.h"
#ifdef CLOUD_GATEWAY_LAB_UPLINK
#include "GatewayCloudUplink.h"
#include <time.h>
#endif
#endif''', 'header include')
header = replace_once(header, '  DataStore* _store;', '''#ifdef CLOUD_GATEWAY_LAB_POLL
  cloud_gateway::PollTarget lab_targets_[gateway_stations::kStationCount];
  bool lab_targets_initialized_ = false;
  uint32_t cloud_event_sequence_ = 0;
  cloud_gateway::TelemetryScheduler lab_scheduler_{
      lab_targets_, gateway_stations::kStationCount, CLOUD_GATEWAY_POLL_INTERVAL_MS, 30000UL};
#endif
  DataStore* _store;''', 'scheduler members')
source = replace_once(source, '    } else if (strcmp(cli_command, "rebuild") == 0) {', '''    } else if (strcmp(cli_command, "cloud setup") == 0) {
#ifdef CLOUD_GATEWAY_LAB_UPLINK
      openGatewayCloudSetup();
#else
      Serial.println("  Cloud setup not available in this build");
#endif
    } else if (strcmp(cli_command, "rebuild") == 0) {''', 'cloud setup rescue CLI')
source = replace_once(source, '#include "MyMesh.h"', '''#ifdef CLOUD_GATEWAY_LAB_POLL
#define GATEWAY_STATIONS_DEFINE_STORAGE
#endif
#include "MyMesh.h"
#ifdef CLOUD_GATEWAY_LAB_UPLINK
void openGatewayCloudSetup();
#endif''', 'station storage definition')
source = replace_once(source, 'void MyMesh::onContactResponse(const ContactInfo &contact, const uint8_t *data, uint8_t len) {\n  uint32_t tag;', '''void MyMesh::onContactResponse(const ContactInfo &contact, const uint8_t *data, uint8_t len) {
  if (len < 4) return;
  uint32_t tag;''', 'response length guard')
source = replace_once(source, '''  memcpy(&tag, data, 4);

  if (pending_login''', '''  memcpy(&tag, data, 4);
#ifdef CLOUD_GATEWAY_LAB_POLL
  const size_t station_slot = lab_scheduler_.currentIndex();
  const auto& station = gateway_stations::active.stations[station_slot];
  if (lab_scheduler_.state() == cloud_gateway::PollState::AwaitingReply &&
      tag == lab_scheduler_.expectedTag() && station.enabled &&
      memcmp(contact.id.pub_key, station.public_key, 32) == 0) {
    Serial.printf("[GATEWAY] RX %s telemetry tag=%08lx bytes=%u payload=",
                  station.node_id, (unsigned long)tag, (unsigned)(len - 4));
    for (uint8_t i = 4; i < len; ++i) Serial.printf("%02x", data[i]);
    Serial.println();
    const auto decoded = cloud_gateway::decodeTelemetry(data + 4, len - 4, station.profile);
    if (decoded.has_voltage)
      Serial.printf("[GATEWAY] %s voltage=%.2f V\\n", station.node_id, decoded.voltage_v);
    if (decoded.has_temperature)
      Serial.printf("[GATEWAY] %s temperature=%.1f C\\n", station.node_id, decoded.temperature_c);
    Serial.printf("[GATEWAY] %s decode_valid=%s humidity=%.1f pressure=%.1f wind=%.2f simulated=%s\\n",
                  station.node_id, decoded.valid ? "yes" : "no", decoded.humidity_pct,
                  decoded.pressure_hpa, decoded.wind_speed_mps,
                  decoded.wind_simulated ? "yes" : "no");
    if (decoded.parsed_bytes != size_t(len - 4))
      Serial.printf("[GATEWAY] %s undecoded_bytes=%u\\n", station.node_id,
                    (unsigned)(size_t(len - 4) - decoded.parsed_bytes));
#ifdef CLOUD_GATEWAY_LAB_UPLINK
    if (decoded.valid && (decoded.has_voltage || decoded.has_temperature ||
                          decoded.has_humidity || decoded.has_pressure || decoded.has_wind)) {
      const time_t utc = time(nullptr);
      if (utc >= 1700000000) {
        struct tm utc_tm;
        gmtime_r(&utc, &utc_tm);
        char timestamp[25];
        strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", &utc_tm);
        gateway_cloud::Reading reading;
        reading.node_id = station.node_id;
        reading.observed_at = timestamp;
        // Bounded independently of the user-chosen node_id (up to 64 bytes).
        // Created once per reception; queue retries preserve the same event ID.
        reading.event_id = String("gw-") + String((unsigned long)utc) + "-" +
                           String((unsigned long)tag, HEX) + "-" +
                           String(++cloud_event_sequence_) + "-" + String((unsigned long)esp_random(), HEX);
        reading.has_voltage = decoded.has_voltage;
        reading.has_temperature = decoded.has_temperature;
        reading.voltage_v = decoded.voltage_v;
        reading.temperature_c = decoded.temperature_c;
        reading.has_humidity = decoded.has_humidity;
        reading.has_pressure = decoded.has_pressure;
        reading.has_wind = decoded.has_wind;
        reading.humidity_pct = decoded.humidity_pct;
        reading.pressure_hpa = decoded.pressure_hpa;
        reading.wind_speed_mps = decoded.wind_speed_mps;
        reading.wind_simulated = decoded.wind_simulated;
        if (!gateway_cloud::enqueue(reading)) Serial.println("[CLOUD] Reading not queued");
      } else {
        Serial.println("[CLOUD] UTC unavailable; skipping upload queue");
      }
    }
#endif
    lab_scheduler_.markReply(millis(), tag);
    return;
  }
#endif

  if (pending_login''', 'response intercept')
source = replace_once(source, '''void MyMesh::loop() {
  BaseChatMesh::loop();''', '''void MyMesh::loop() {
  BaseChatMesh::loop();
#ifdef CLOUD_GATEWAY_LAB_POLL
  if (!lab_targets_initialized_) {
    gateway_stations::begin();
    for (size_t i = 0; i < gateway_stations::kStationCount; ++i) {
      const auto& s = gateway_stations::active.stations[i];
      lab_targets_[i] = cloud_gateway::PollTarget(s.node_id, s.public_key, 32, s.enabled);
    }
    lab_targets_initialized_ = true;
  }
#ifdef CLOUD_GATEWAY_LAB_UPLINK
  lab_scheduler_.setIntervalMs(gateway_cloud::poll_interval_ms);
#endif
  const uint32_t now = millis();
  const char* waiting_node = lab_targets_[lab_scheduler_.currentIndex()].name;
  if (lab_scheduler_.tick(now)) Serial.printf("[GATEWAY] %s timeout\\n", waiting_node);
  // Never compete with a phone's outstanding request.
  const bool app_busy = pending_login || pending_status || pending_telemetry ||
                        pending_discovery || pending_req;
  if (app_busy && lab_scheduler_.state() == cloud_gateway::PollState::AwaitingReply) {
    lab_scheduler_.pauseForCompanion(now);
    Serial.println("[GATEWAY] Poll canceled: Companion request takes priority");
  }
  if (const auto* target = lab_scheduler_.next(now, app_busy)) {
    ContactInfo* contact = lookupContactByPubKey(target->public_key, target->public_key_size);
    if (!contact) {
      Serial.printf("[GATEWAY] %s contact not found; add it in MeshCore app; skipping\\n", target->name);
      lab_scheduler_.skip(now);
    } else {
      uint32_t tag = 0, estimated_timeout = 0;
      int result = sendRequest(*contact, REQ_TYPE_GET_TELEMETRY_DATA, tag, estimated_timeout);
      if (result != MSG_SEND_FAILED) {
        lab_scheduler_.markSent(now, tag);
        Serial.printf("[GATEWAY] TX %s tag=%08lx timeout_est=%lu ms\\n",
                      target->name, (unsigned long)tag, (unsigned long)estimated_timeout);
      } else {
        Serial.printf("[GATEWAY] %s send failed; skipping until next cycle\\n", target->name);
        lab_scheduler_.skip(now);
      }
    }
  }
#endif''', 'loop')

# Build defaults are used only until the operator saves the first station form.
# Generated source and shared headers travel with the patched checkout (BLE too).
import json
import shutil
if args.public_key.lower() in ("00"*32, "ff"*32):
    parser.error("invalid public key")
profile_lines = ["s.profile = cloud_gateway::TelemetryProfile();"]
if args.profile == "rak-real":
    profile_lines = ["s.profile = cloud_gateway::rak4631RealWindProfile();"]
elif args.profile == "rak-simulated":
    profile_lines = ["s.profile = cloud_gateway::rak4631SimulatedWindProfile();"]
for measurement in ("voltage", "temperature", "humidity", "pressure", "wind"):
    channel = getattr(args, measurement + "_channel")
    if channel is not None:
        if not -1 <= channel <= 255:
            parser.error("channel must be -1 or 0..255")
        profile_lines.append(f"s.profile.{measurement}_channel = {channel};")
key_bytes = ",".join("0x"+args.public_key[i:i+2] for i in range(0,64,2))
defaults = '''#pragma once
#include "StationConfig.h"
namespace gateway_stations {
inline Station buildDefaultStation() {
  Station s;
  s.enabled = true;
  strcpy(s.node_id, NODE_ID);
  strcpy(s.label, NODE_ID);
  const uint8_t key[32] = {KEY_BYTES};
  memcpy(s.public_key, key, sizeof key);
  PROFILE
  return s;
}
}
'''.replace("NODE_ID",json.dumps(args.node_id)).replace("KEY_BYTES",key_bytes).replace("PROFILE","\n  ".join(profile_lines))
# The display name has a smaller bound than node_id.
defaults=defaults.replace('strcpy(s.label, '+json.dumps(args.node_id)+');',
                          'strncpy(s.label, '+json.dumps(args.node_id)+', sizeof s.label - 1);')
for name in ("StationConfig.h", "GatewayStations.h", "GatewayStationPortal.h"):
    shutil.copyfile(Path(__file__).resolve().parents[1]/"include"/name, cpp.parent/name)
(cpp.parent/"GatewayStationDefaults.h").write_text(defaults)
cpp.write_text(source)
hdr.write_text(header)
print("Applied configurable two-station LAB patch to", root)
