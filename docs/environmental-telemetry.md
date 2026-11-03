# Environmental telemetry: HTTPS first, MQTT optional

The existing LAB path is MeshCore reply → portable C++ CayenneLPP decoder →
16-entry RAM queue → verified HTTPS POST `/v1/telemetry` → Flask → BigQuery.
MQTT is not required. `cloud/mqtt_bridge.py` is an optional external adapter;
its dependencies are separate from the API image and firmware.

## Device mapping and units

The default firmware profile retains voltage and temperature on channel 1.
`rak4631SimulatedWindProfile()` explicitly selects voltage on 1, BME280
on 2 (temperature °C, humidity %, pressure hPa), analog input on 3 (m/s).
LPP types are 0x74, 0x67, 0x68, 0x73 and 0x02 respectively. Multibyte
values are big-endian; temperature and analog input are signed. Analog input
resolution is 0.01; humidity is 0.5 and pressure/temperature are 0.1.

Channel assignments belong to the device profile, not to the sensor type.
An analog zero on an unconfigured channel is never promoted to wind.
A configured virtual wind must equal zero and carries `wind_simulated: true`.
Real wind can be zero with `wind_simulated: false`; omitted metadata stays
unknown (`null`) for backwards compatibility. Missing measurements stay absent
or null; zero is a measurement. The profile must change when real wind hardware
is fitted. This implementation does not calibrate an analog voltage to wind.

The decoder skips known but unmapped types. Unknown types, truncated records,
out-of-range mapped values and duplicate mapped measurements prevent firmware
upload of the frame. `tools/inspect_telemetry.py` remains a diagnostic tool that
returns decoded prefixes plus unparsed suffixes (including the old GAT562
capture's suffix); it does not certify a frame for ingestion. The default
GAT562 profile explicitly allows the four zero padding bytes of that validated
capture; the RAK profile does not. The optional raw adapter uses the same
per-profile allowance. Other unknown suffixes are rejected.

## Select the actual polling target

The existing CI workflow retains the historical GAT562 target by default.
`firmware/config/nodes.example.json` is descriptive; it is not loaded at runtime.
To prepare a RAK LAB build, invoke the patch against a clean upstream checkout,
using its **actual** contact public key (64 hexadecimal characters):

```sh
python firmware/scripts/apply_lab_patch.py /path/to/upstream \
  --node-id RAK4631-LAB --public-key "$RAK_PUBLIC_KEY" --profile rak-simulated
```

Use `--temperature-channel`, `--humidity-channel`, `--pressure-channel`,
`--voltage-channel`, `--wind-channel` to override individual assignments
(-1 disables a measurement). The patch binds that profile to the verified
public key and response tag. It still polls one target, like the existing LAB
implementation. Copy the headers and build with the existing Wi-Fi workflow's
flags. The RAK public key has not been supplied, so no identity is guessed.

## API and BigQuery

Existing flat voltage/temperature JSON continues to work. New nullable fields:
`humidity_pct` (0..100), `pressure_hpa` (0..2000), `wind_speed_mps` (0..100),
`wind_simulated` (boolean/null, requires wind when provided).
Booleans as numbers, strings, NaN and infinity are rejected. At least one
measurement is required. Units must already be normalized for direct HTTPS.
`cloud/bigquery.sql` contains both table creation and idempotent additive
ALTER statements for existing tables. Review and apply these to a test dataset
before running the new API; no SQL has been executed against GCP.

## Reproducible local checks

Use Python 3.12 (the API container/CI version) and a C++11 compiler:

```sh
python -m pip install -r cloud/requirements.txt
python -m unittest discover -s cloud/tests -v
python -m unittest discover -s tests -v
```

Tests compile the actual portable firmware decoder, check the historical
capture and signed values, remapped channels, virtual/real zero, bad ranges,
truncation, unknown types and duplicates. The integration test feeds RAK hex
through normalization and the Flask endpoint into a mocked BigQuery client.
No real broker, radio, HTTPS endpoint or BigQuery service is contacted.

## End-to-end LAB acceptance (manual)

1. Review the patch and build the Wi-Fi LAB firmware against a pinned upstream
   MeshCore revision. The existing workflow tracks upstream main; record its
   exact SHA. Confirm the RAK identity and profile before flashing.
2. On a test dataset, review/apply the additive schema migration; run the API
   with test-only credentials. Resolve Cloud Run IAM invocation separately from
   the application's bearer token. Do not loosen production IAM to test this.
3. Request telemetry from the actual RAK. Save the payload after the response
   tag and inspect it with `python tools/inspect_telemetry.py HEX`. Confirm types,
   channels, BME280 readings, and analog zero. No timestamp is invented: the
   gateway queues only after UTC synchronization.
4. Configure the existing HTTPS LAB uplink with a trusted CA and test endpoint.
   Confirm HTTP 202 and inspect the row in BigQuery, filtering on observed_at
   and node_id: compare temperature/humidity/pressure, verify wind_speed_mps=0
   and wind_simulated=true. Compare event_id against the sent event.
5. Interrupt connectivity, restore it and verify queued retries keep event_id.
   The queue is RAM-only and lost on reboot; full queues drop the newest event.
   BigQuery insertId deduplication is best effort. Validate the old GAT562 flat
   payload too, and a real-zero profile with wind_simulated=false.
6. Obtain validation before any production release or deployment.

## Optional MQTT adapter

Install `cloud/requirements-mqtt.txt` only for this adapter. It accepts either
flat API JSON, or `{node_id, event_id, observed_at, lpp_hex}` with a trusted
local mapping (see `cloud/profiles.example.json`). Replace example identities
with the actual ones. Mixed raw/flat measurements and ambiguous mappings are
rejected. Stable event IDs and timestamps must originate at the publisher,
not be generated on redelivery. No MeshCore-to-MQTT radio publisher is supplied.

Set MQTT_HOST, MQTT_PORT (default 8883), MQTT_TOPIC, MQTT_CLIENT_ID (stable),
MQTT_CA if needed, MQTT_USERNAME/MQTT_PASSWORD if required, INGEST_URL (HTTPS)
and INGEST_TOKEN, then run:

```sh
python cloud/mqtt_bridge.py cloud/profiles.example.json
```

Use QoS 1 publications and broker persistent sessions. TLS verification is
mandatory. Manual MQTT ACK occurs only after HTTP 202. Failure disconnects and
exits nonzero: run under a supervisor for redelivery. Invalid messages require
operator quarantine before restart. This is a LAB adapter, without a dead-letter
queue or IAM identity-token flow. Validate broker redelivery and duplicates in
LAB before relying on it. Direct HTTPS needs none of this MQTT setup.
