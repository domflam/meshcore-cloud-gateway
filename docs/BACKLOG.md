# Project backlog — MeshCore Cloud Gateway & Weather Station

Updated: 2026-10-13. Statuses reflect the **laboratory project**, not upstream MeshCore. `Done (lab)` means verified in testing; it does **not** imply merged into `main` or deployed at the archery club.

## P0 — Proven telemetry chain (done in lab)

- [x] **LAB-01 — Receive GAT562-01 telemetry on Heltec V3.** Decode battery voltage and temperature from remote MeshCore telemetry.
- [x] **LAB-02 — Wi-Fi gateway configuration.** Persist configuration across firmware flashes / restarts and support periodic telemetry polling.
- [x] **LAB-03 — Authenticated cloud forwarding.** HTTPS POST to Cloud Run using Bearer authentication, certificate validation, and retry after transient network errors.
- [x] **LAB-04 — Store real observations in BigQuery.** Validate `meshcore-cloud-gateway.meshcore.telemetry` with actual GAT562 rows.
- [ ] **LAB-05 — Consolidate tested feature branches.** Review changes, CI, secrets and compatibility before merging; do not assume `main` contains the validated POC.

## P1 — Solar weather station V1 (next)

- [ ] **WX-01 — BME280 integration.** Connect on RAK19007 I²C, read temperature (°C), relative humidity (%) and pressure (hPa). **Acceptance:** repeatable sensor reads and graceful handling of missing sensor.
- [ ] **WX-02 — Passive anemometer bench setup.** Test two Lextronic LEXCA003 units; verify RJ11 contact pins, reed behavior, pulse/revolution specification and conversion calibration. **Acceptance:** counted pulses agree with controlled manual rotation.
- [ ] **WX-03 — RAK4631 pulse acquisition.** Select a verified available 3.3 V GPIO, implement interrupt counting and reed debounce; preserve MeshCore operation and low-power sleep. **Acceptance:** no false pulses or missed events in repeatable bench tests.
- [ ] **WX-04 — Wind metrics.** Calculate mean wind over a documented period (initial target: 10 minutes) and an estimated maximum gust over rolling 3-second windows. Account for low pulse frequency and document resolution/accuracy limitations. **Acceptance:** reproducible tests with simulated pulses and real sensor.
- [ ] **WX-05 — Sensor telemetry schema v1.** Define node ID, timestamp, units, battery, BME280 values, mean wind and gust; choose a compact, versioned MeshCore-compatible encoding. **Acceptance:** payload and sample vectors documented.
- [ ] **WX-06 — Gateway decoder & cloud schema.** Extend Heltec decoding, Cloud Run validation and BigQuery schema for weather values; preserve compatibility with existing GAT562 records. **Acceptance:** complete RAK4631 → Heltec → Cloud Run → BigQuery test.
- [ ] **WX-07 — Solar power profiling.** Measure sleep/active draw, radio duty cycle and impact of continuous wind pulse capture; validate solar and battery autonomy. **Acceptance:** measured power budget and test report.
- [ ] **WX-08 — Outdoor installation.** Weatherproof enclosure, cable glands, wind sensor mounting, lightning/ESD considerations, and field calibration. **Acceptance:** sustained operation and plausible readings in outdoor conditions.

## P1 — Dashboard and data access

- [x] **WEB-01 — Build dashboard source prototype.** Flask page, `/api/weather`, `/health`, current values and a 24-hour temperature chart on branch `feature/weather-dashboard-prototype`. **Code exists; not deployed.**
- [ ] **WEB-02 — Deploy dashboard.** Separate Cloud Run service, dedicated least-privilege BigQuery identity, confirm access policy. **Acceptance:** working URL, verified read-only queries and successful health check.
- [ ] **WEB-03 — Add weather metrics.** Humidity, pressure, mean wind, 3-second gust, battery, station last-seen and stale-data indicator. **Acceptance:** responsive mobile page with correct units.
- [ ] **WEB-04 — History and embedding.** Wind chart, 7-day history, mobile/PWA layout and club website embed after agreeing on publication needs. **Acceptance:** embedded view works without exposing ingestion secrets.
- [ ] **WEB-05 — Operational controls.** Query-cost limits, service monitoring, data retention and alerting for stale or anomalous observations.

## P2 — Improvements / later versions

- [ ] **NET-01 — Airtime-aware reporting.** Periodic summaries and configurable change/threshold triggers, respecting mesh airtime and radio regulations.
- [ ] **NET-02 — Offline resilience.** Buffer/retry behavior and deduplication across gateway reconnects.
- [ ] **NET-03 — Multi-station support.** Device inventory, station-specific views and health metrics.
- [ ] **WX-09 — Wind direction.** Optional vane sensor after V1 validation.
- [ ] **WX-10 — Rain gauge.** Optional tipping-bucket measurement after V1 validation.
- [ ] **COMP-01 — Evaluate WeatherXM D2 Mesh interoperability.** Track published firmware, telemetry conventions and packet formats when available; **no dependency or compatibility claim today**.
- [ ] **DOC-01 — Hardware wiring and build guide.** Confirmed pin maps, photos, BOM, calibration procedure and reproducible firmware builds.
- [ ] **DOC-02 — Upstream maintenance strategy.** Record upstream MeshCore base version, changes carried by this project and a repeatable rebase/merge approach.

## Non-goals for V1

- Wind direction and rainfall.
- Replacing the core MeshCore networking stack.
- Claiming certified meteorological accuracy.
- Depending on WeatherXM hardware, firmware or protocols.

## Links

- [Repository](https://github.com/domflam/meshcore-cloud-gateway)
- [Heltec cloud uplink development](https://github.com/domflam/meshcore-cloud-gateway/tree/feature/heltec-cloud-uplink-v05)
- [Dashboard prototype PR #8](https://github.com/domflam/meshcore-cloud-gateway/pull/8)
- [Upstream MeshCore](https://github.com/ripplebiz/MeshCore)
