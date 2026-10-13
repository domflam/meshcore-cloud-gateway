#!/usr/bin/env python3
"""Apply minimal LAB-only BLE telemetry poller to a checked-out MeshCore source tree.

Fails closed if expected upstream anchors have changed.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1])
cpp = root / "examples/companion_radio/MyMesh.cpp"
hdr = root / "examples/companion_radio/MyMesh.h"
source = cpp.read_text()
header = hdr.read_text()

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

header = replace_once(header, '#include "AbstractUITask.h"', '#include "AbstractUITask.h"\n#ifdef CLOUD_GATEWAY_LAB_POLL\n#include "TelemetryScheduler.h"\n#include "TelemetryDecoder.h"\n#endif', 'header include')
header = replace_once(header, '  DataStore* _store;', '''#ifdef CLOUD_GATEWAY_LAB_POLL
  static const uint8_t kGatPublicKey[32];
  cloud_gateway::PollTarget lab_targets_[1] = {{"GAT562-01", kGatPublicKey, 32}};
  uint32_t cloud_event_sequence_ = 0;\n  cloud_gateway::TelemetryScheduler lab_scheduler_{
      lab_targets_, 1, CLOUD_GATEWAY_POLL_INTERVAL_MS, 30000UL};
#endif
  DataStore* _store;''', 'scheduler members')
source = replace_once(source, '    } else if (strcmp(cli_command, "rebuild") == 0) {', '''    } else if (strcmp(cli_command, "cloud setup") == 0) {
#ifdef CLOUD_GATEWAY_LAB_UPLINK
      openGatewayCloudSetup();
#else
      Serial.println("  Cloud setup not available in this build");
#endif
    } else if (strcmp(cli_command, "rebuild") == 0) {''', 'cloud setup rescue CLI')
source = replace_once(source, '#include "MyMesh.h"', '''#include "MyMesh.h"
#ifdef CLOUD_GATEWAY_LAB_UPLINK
#include "GatewayWifiProvisioning.h"
#endif
#ifdef CLOUD_GATEWAY_LAB_POLL
const uint8_t MyMesh::kGatPublicKey[32] = {\n  0x26,0xb5,0x98,0x6e,0xc5,0x21,0xb6,0x2b,\n  0x98,0x11,0x68,0x85,0x13,0xf9,0xa7,0x20,\n  0xb5,0x24,0x5c,0xd9,0x44,0x8f,0x90,0xd4,\n  0xcb,0xe3,0xe0,0xca,0x23,0xc8,0x17,0xca\n};
#endif''', 'static key definition')
source = replace_once(source, 'void MyMesh::onContactResponse(const ContactInfo &contact, const uint8_t *data, uint8_t len) {\n  uint32_t tag;', '''void MyMesh::onContactResponse(const ContactInfo &contact, const uint8_t *data, uint8_t len) {
  if (len < 4) return;
  uint32_t tag;''', 'response length guard')
source = replace_once(source, '''  memcpy(&tag, data, 4);

  if (pending_login''', '''  memcpy(&tag, data, 4);
#ifdef CLOUD_GATEWAY_LAB_POLL
  if (lab_scheduler_.state() == cloud_gateway::PollState::AwaitingReply &&
      tag == lab_scheduler_.expectedTag() &&
      memcmp(contact.id.pub_key, kGatPublicKey, 32) == 0) {
    Serial.printf("[GATEWAY] RX GAT562 telemetry tag=%08lx bytes=%u payload=",
                  (unsigned long)tag, (unsigned)(len - 4));
    for (uint8_t i = 4; i < len; ++i) Serial.printf("%02x", data[i]);
    Serial.println();
    const auto decoded = cloud_gateway::decodeTelemetry(data + 4, len - 4);
    if (decoded.has_voltage) {
      Serial.printf("[GATEWAY] GAT562 voltage=%.2f V\\n", decoded.voltage_v);
    }
    if (decoded.has_temperature) {
      Serial.printf("[GATEWAY] GAT562 temperature=%.1f C\\n", decoded.temperature_c);
    }
    if (decoded.parsed_bytes != size_t(len - 4)) {
      Serial.printf("[GATEWAY] GAT562 undecoded_bytes=%u\\n",
                    (unsigned)(size_t(len - 4) - decoded.parsed_bytes));
    }
#ifdef CLOUD_GATEWAY_LAB_UPLINK
    if (decoded.has_voltage || decoded.has_temperature) {
      const time_t utc = time(nullptr);
      if (utc >= 1700000000) {
        struct tm utc_tm;
        gmtime_r(&utc, &utc_tm);
        char timestamp[25];
        strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", &utc_tm);
        gateway_cloud::Reading reading;
        reading.node_id = "GAT562-01";
        reading.observed_at = timestamp;
        reading.event_id = String("gat562-") + String((unsigned long)utc) + "-" +
                           String((unsigned long)tag, HEX) + "-" +
                           String(++cloud_event_sequence_);
        reading.has_voltage = decoded.has_voltage;
        reading.has_temperature = decoded.has_temperature;
        reading.voltage_v = decoded.voltage_v;
        reading.temperature_c = decoded.temperature_c;
        if (!gateway_cloud::enqueue(reading))
          Serial.println("[CLOUD] Reading not queued");
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
  const uint32_t now = millis();
  if (lab_scheduler_.tick(now)) Serial.println("[GATEWAY] GAT562 timeout");
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
      // This node must already be in the Companion contact list.
      static uint32_t last_missing_log = 0;
      if (now - last_missing_log >= 30000UL) {
        Serial.println("[GATEWAY] GAT562 contact not found; add it in MeshCore app");
        last_missing_log = now;
      }
    } else {
      uint32_t tag = 0, estimated_timeout = 0;
      int result = sendRequest(*contact, REQ_TYPE_GET_TELEMETRY_DATA, tag, estimated_timeout);
      if (result != MSG_SEND_FAILED) {
        lab_scheduler_.markSent(now, tag);
        Serial.printf("[GATEWAY] TX GAT562 tag=%08lx timeout_est=%lu ms\\n",
                      (unsigned long)tag, (unsigned long)estimated_timeout);
      } else {
        Serial.println("[GATEWAY] Send failed; will retry");
      }
    }
  }
#endif''', 'loop')
header = replace_once(header, '#include "TelemetryDecoder.h"', '#include "TelemetryDecoder.h"\n#ifdef CLOUD_GATEWAY_LAB_UPLINK\n#include "GatewayCloudUplink.h"\n#include <time.h>\n#endif', 'cloud include')
cpp.write_text(source)
hdr.write_text(header)
print("Applied LAB telemetry patch to", root)
