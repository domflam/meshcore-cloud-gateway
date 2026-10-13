# MeshCore Cloud Gateway & Solar Weather Station

**Experimental MeshCore extension for remote telemetry, solar-powered weather sensing, and cloud visualization.**

This project explores a lightweight, end-to-end architecture: a remote LoRa/MeshCore node sends sensor observations to a Wi-Fi gateway, which forwards them securely to Google Cloud for storage and visualization. The initial use case is a weather station for an archery club, with particular attention to **wind speed and gusts**, low power consumption, and long-range connectivity.

> **Project status:** laboratory proof of concept. The GAT562-to-BigQuery telemetry chain has been validated; the RAK4631 weather sensors and dashboard deployment are still under development. This is not an official MeshCore distribution or WeatherXM product.

## Architecture

```text
CURRENT LAB POC
GAT562-01 (MeshCore telemetry)
        │ LoRa / MeshCore
        ▼
Heltec WiFi LoRa 32 V3 (gateway)
        │ HTTPS + Bearer token
        ▼
Google Cloud Run (Flask ingestion)
        │
        ▼
BigQuery (meshcore.telemetry)
        │
        └── Weather dashboard prototype (not deployed yet)

TARGET WEATHER V1
BME280 (temperature, humidity, pressure) ─┐
                                          ├── RAK4631 / RAK19007 solar node
Passive reed anemometer (wind pulses) ─────┘           │
                                            MeshCore / LoRa
                                                      ▼
                                             Heltec Wi-Fi gateway
                                                      ▼
                                         Cloud Run → BigQuery → Web/PWA
```

The remote station is intended to operate without Wi-Fi or cellular access. Internet access is required only at the gateway for cloud forwarding.

## What has been implemented

- **GAT562 telemetry reception:** gateway decodes remote node battery voltage and temperature.
- **Heltec V3 Wi-Fi gateway:** configurable Wi-Fi, periodic polling and telemetry uplink.
- **Cloud ingestion:** authenticated HTTPS POST to a Flask service on Cloud Run, with retries after transient failures.
- **BigQuery storage:** end-to-end ingestion verified with real laboratory observations.
- **Dashboard code prototype:** Flask + responsive HTML, JSON endpoint and temperature history chart; **not yet deployed or validated in production**.

These developments live on feature branches / pull requests and are **not necessarily merged into `main`**:
- [Heltec cloud uplink branch](https://github.com/domflam/meshcore-cloud-gateway/tree/feature/heltec-cloud-uplink-v05)
- [Weather dashboard prototype (PR #8)](https://github.com/domflam/meshcore-cloud-gateway/pull/8)

## Weather station V1 — planned hardware

| Component | Purpose | Status |
| --- | --- | --- |
| RAK4631 + RAK19007 | Low-power MeshCore solar station | Integration planned |
| BME280 | Temperature, humidity, pressure | Sensor integration pending |
| Lextronic LEXCA003 × 2 | Passive reed anemometers for lab/field tests | Purchase planned; not yet tested |
| Heltec WiFi LoRa 32 V3 | MeshCore-to-HTTPS gateway | Laboratory uplink validated |
| Cloud Run + BigQuery | Ingestion and history | Laboratory path validated |

V1 scope: temperature, humidity, pressure, **mean wind speed** and **3-second gust estimate**. Wind direction and rainfall are deferred to a later version. Wind sensor calibration, RJ11 pinout, GPIO allocation, debounce and low-speed gust accuracy must be verified on real hardware.

## Development priorities

See **[Project backlog](docs/BACKLOG.md)** for delivered capabilities, open work, acceptance criteria and later ideas.

Immediate next steps:
1. Integrate the BME280 and passive pulse anemometer on RAK4631 without disrupting MeshCore or solar autonomy.
2. Define and version the weather telemetry payload; test gateway decoding and BigQuery schema evolution.
3. Deploy and validate the read-only weather dashboard on a separate Cloud Run service.
4. Test outdoors, calibrate wind readings and document power consumption.

## Repository layout

- `examples/`, `src/`, `docs/` and other existing MeshCore directories: upstream-derived embedded code and documentation.
- `prototype/weather-dashboard/`: experimental Flask dashboard (**feature branch**).
- `docs/BACKLOG.md`: our project-specific roadmap.
- `docs/upstream-meshcore-readme.md`: preserved upstream README as it appeared before this project-specific rewrite.

## Origin, fork and license

This repository is **derived from [MeshCore by ripplebiz](https://github.com/ripplebiz/MeshCore)**, a lightweight LoRa multi-hop networking project. It retains upstream MeshCore code while adding experiments around sensor telemetry, Wi-Fi/cloud gateway integration, Google Cloud ingestion, and a solar weather station.

**This is an independent experimental extension, not an official MeshCore release.** Our feature branches and files may differ from upstream, and upstream instructions or roadmaps do not necessarily describe this project's current state.

The original MeshCore README is preserved at [docs/upstream-meshcore-readme.md](docs/upstream-meshcore-readme.md). The upstream MIT license and copyright notice are retained in [license.txt](license.txt); consult individual files for any additional notices. Please respect upstream licenses and attribution when reusing code.

For the original firmware, flashing tools, clients and general MeshCore documentation, visit [MeshCore](https://github.com/ripplebiz/MeshCore) and [docs.meshcore.io](https://docs.meshcore.io).

## Security and operational notes

- Keep Wi-Fi credentials, API tokens and cloud secrets **out of Git**.
- Prefer a dedicated read-only BigQuery service account for the dashboard.
- Validate power budget, pin voltage levels and weatherproofing before unattended installation.
- Mesh radio airtime and telemetry cadence must respect local regulations and network etiquette.

## Contributing

This repository currently serves as a project laboratory. Please open an issue or propose a PR against the relevant project branch before making substantial changes. The upstream MeshCore contribution guidelines apply to contributions **to upstream**, not automatically to this fork.
