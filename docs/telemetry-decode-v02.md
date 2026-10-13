# Telemetry decode V0.2 — verified CayenneLPP fields

The working V0.1 firmware remains unchanged. This branch adds an offline
CayenneLPP inspector and regression tests.

## Observed GAT562 capture

```text
[GATEWAY] TX GAT562 tag=6acdf14d timeout_est=2694 ms
[GATEWAY] RX GAT562 telemetry tag=6acdf14d bytes=12 payload=0174019b016700d400000000
```

Known CayenneLPP records (channel, sensor type, big-endian value):
- `01 74 01 9b`: channel 1, voltage 0x019b * 0.01 = **4.11 V**.
- `01 67 00 d4`: channel 1, temperature 0x00d4 * 0.1 = **21.2 °C**.
- `00 00 00 00`: unknown/unparsed suffix; do not assign a meaning yet.

Companion screenshot: **4.11 V, 22.5 °C, 92%**. Voltage matches;
temperature likely changed between captures, but simultaneous verification
is needed. The battery percentage is derived by the app from voltage; the
capture does not contain a validated explicit state-of-charge field.

Reference: MeshCore CayenneLPP telemetry and LPP sensor type codes.
- https://github.com/cbattlegear/MeshCoreOne-Android/blob/main/MeshCore/Sources/MeshCore/MeshCore.docc/Articles/Telemetry.md
- https://meshcore-dev.github.io/meshcore-ha/docs/ha/sensors/

## Run tests and inspect

```sh
python3 tools/inspect_telemetry.py 0174019b016700d400000000
python3 -m unittest discover -s tests -p 'test_telemetry_inspect.py'
```

The tool does not touch radio/BLE firmware. Unknown and truncated records
are left as raw hex, never fabricated.

## Next steps
1. Collect a simultaneous Companion screenshot and serial payload.
2. Inspect the four trailing zero bytes in the precise firmware schema.
3. Port this bounded decoder to the LAB firmware and run the BLE build.
4. Flash only after the build is green and then verify readings on hardware.
5. Add HTTPS upload to Cloud Run and BigQuery after device-side verification.
