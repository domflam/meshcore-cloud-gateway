# MeshCore Cloud Gateway — POC architecture

Status: design proposal; no firmware modification yet.

## Goal

Use one Heltec WiFi LoRa 32 V3 (ESP32-S3 / SX1262) to poll native MeshCore repeater telemetry from a GAT562 30S and a RAK4631 (weather station), then publish normalized measurements over Wi-Fi/TLS to a Google Cloud Run ingestion API. No phone, Raspberry Pi, or external MQTT broker is required during autonomous operation.

## Baseline

- Upstream: https://github.com/meshcore-dev/MeshCore
- Firmware role: Companion radio; preserve normal mobile-app access.
- Candidate target: `Heltec_v3_companion_radio_wifi` (verify current upstream build flags and transport compatibility before implementation).
- Key files to inspect: `examples/companion_radio/MyMesh.cpp`, `MyMesh.h`, `variants/heltec_v3/platformio.ini`, and companion protocol documentation.
- The user has validated manually that the Heltec V3 Companion can request telemetry from both GAT562 and RAK4631 using the mobile application. Autonomous polling is not yet validated.

## Critical integration constraint

The Companion implementation tracks outstanding telemetry requests with `pending_telemetry` and may clear other pending request state when new requests start. Do not issue parallel polling requests. Implement a state machine that submits one request, awaits matching radio response or timeout, and only then advances to the next node. Mobile-app commands must take precedence, or polling must pause while the app is active.

## Suggested modules

1. `TelemetryScheduler`: configured peer public keys / contact identifiers, poll interval (initially 15 min), jitter, sequential state machine, timeout and retries.
2. `TelemetryDecoder`: reuse upstream response parsing / CayenneLPP where possible; distinguish native repeater system metrics from environmental sensors and handle missing fields.
3. `CloudPublisher`: HTTPS POST with bounded queue, connection timeout, retry/backoff, authentication header and idempotency key; never block radio processing.
4. `GatewayConfig`: persisted Wi-Fi credentials, Cloud Run URL/token and contact allowlist. Never commit secrets.

## Example normalized payload (illustrative, not confirmed wire format)

```json
{
  "gateway_id": "heltec-v3-lab-01",
  "node_id": "gat562-01",
  "observed_at": "2026-10-12T17:00:00Z",
  "source": "meshcore-native-telemetry",
  "measurements": {
    "battery_voltage_v": 4.01
  }
}
```

Only include measurement keys actually present in a decoded response. The gateway should timestamp receipt using a synchronized clock (NTP or other validated source).

## Milestones and acceptance criteria

### v0.1 — autonomous polling
- Boot without phone; configured GAT562 telemetry request sent periodically.
- Decode reply and print structured logs via USB serial.
- Sequentially poll RAK4631 after GAT562; verify timeout and absent-node behavior.
- Mobile Companion usage still works and is prioritized.

### v0.2 — cloud uplink
- Wi-Fi auto-reconnect, NTP time, HTTPS POST to configurable Cloud Run endpoint.
- Explicit authentication; secrets excluded from source and logs.
- Bounded queue and retry/backoff; no blocking in LoRa loop.
- Basic end-to-end test with Cloud Run and BigQuery.

### v0.3 — operational hardening
- Node allowlist and configuration persistence.
- Deduplication/idempotency, observability, failure counters, reboot recovery.
- Measure radio impact, RAM/heap, Wi-Fi reconnect behavior and duty-cycle compliance.

## Validation checklist

- Identify the exact mobile-command handler for `CMD_REQ_TELEMETRY`, radio send method and asynchronous response callback in the pinned upstream revision.
- Confirm how the Companion transports coexist on the Heltec V3 (BLE/USB/Wi-Fi).
- Check whether native BME280 readings are actually present in repeater telemetry; do not assume upstream automatically exposes them.
- Confirm secure Cloud Run authentication feasible on device (API gateway token or other suitable approach).
- Build and flash LAB-01 first; leave FIELD-01 untouched until successful soak testing.
- Respect regional 868 MHz duty-cycle requirements and avoid unnecessary polling.

## Firmware strategy

Prefer a small, reviewable delta against pinned upstream MeshCore. Compare the existing OffbandMesh Wi-Fi/MQTT work for reusable networking patterns, but do not import MQTT or an entire fork unless needed.

References:
- https://github.com/meshcore-dev/MeshCore
- https://github.com/meshcore-dev/MeshCore/blob/main/examples/companion_radio/MyMesh.h
- https://github.com/OffbandMesh/meshcore-firmware
