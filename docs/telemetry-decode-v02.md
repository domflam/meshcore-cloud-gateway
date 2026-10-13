# Telemetry decode V0.2 — capture and verification

## Confirmed hardware POC
Heltec V3 Companion BLE + autonomous GAT562 poller returned:

```text
[GATEWAY] TX GAT562 tag=6acdf14d timeout_est=2694 ms
[GATEWAY] RX GAT562 telemetry tag=6acdf14d bytes=12 payload=0174019b016700d400000000
```

The matching tags confirm response correlation. The payload is **12 bytes**, not yet
a verified list of sensor readings. Do not label any offsets as temperature,
humidity, battery, pressure, etc. without checking the upstream MeshCore
telemetry serialization and the GAT562 device's advertised sensor types.

## Non-invasive inspection
```sh
python3 tools/inspect_telemetry.py 0174019b016700d400000000
python3 -m unittest discover -s tests -p 'test_telemetry_inspect.py'
```

The tool prints octets and candidate 16-bit integer interpretations for
diagnostics. These are **not decoded MeshCore fields**. It does not change
firmware, BLE behavior, or radio scheduling.

## Next implementation gate
1. Identify upstream MeshCore telemetry wire schema, version, type identifiers
   and byte order in the precise upstream revision used by the LAB build.
2. Capture a second GAT562 payload alongside the values displayed in MeshCore
   Companion and compare; do not infer fields from a single sample.
3. Implement schema-aware C++ decoder with bounds checks and golden tests.
4. Compile the LAB firmware and validate decoded values against the app.
5. Only then add Wi-Fi HTTPS ingestion into Cloud Run / BigQuery.

## Regression requirements
- Existing BLE Companion functionality remains available.
- Autonomous requests must yield to Companion traffic.
- Unknown or malformed telemetry must be logged as raw hex, never fabricated.
- Preserve the successful V0.1 firmware / PR #3.
