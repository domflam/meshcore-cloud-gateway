# V0.5 — Heltec uplink (work in progress)

## Confirmed baseline
- V0.4 Cloud Run API accepted a simulated measurement, persisted in BigQuery.
- Heltec Wi-Fi provisioning works on the laboratory device.
- GAT562 CayenneLPP voltage and temperature decoding was previously verified.
- Cloud Run currently requires IAM invoker permission, **not** just an
  application Bearer token.

## Safe integration plan
1. Add a bounded RAM queue to decouple MeshCore callbacks from HTTP.
2. Build a stable event ID per received reading; retain it across retries.
3. Derive `observed_at` from synchronized UTC time; do not invent timestamps.
4. Connect the actual decoded telemetry callback to the queue. Verify exact
   callback symbols against the pinned upstream MeshCore source before patching.
5. Provision a device-facing authenticated endpoint without exposing the
   existing Cloud Run service anonymously. Evaluate API Gateway or a separate
   constrained ingress with per-device credentials, quotas, and rotation.
6. Use verified TLS certificates, bounded timeouts, exponential backoff and
   HTTP 202 acknowledgement before removing a queued event.
7. Flash and confirm an actual GAT562 reading in BigQuery.

## Current code status
`firmware/include/GatewayCloudUplink.h` provides a LAB HTTPS queue/uplink,
injected by `apply_lab_patch.py` when CLOUD_GATEWAY_LAB_UPLINK is enabled.
Its queue holds 16 readings in RAM, lost on reboot. The repository does not
establish the current deployed state. See [environmental telemetry](environmental-telemetry.md)
for device-specific profiles, new environmental fields and end-to-end checks.

Do not commit tokens to Git, flash them in published firmware, or disable
TLS verification. The current Wi-Fi setup AP password is a lab default and
must be hardened before unattended installation.
