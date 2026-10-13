# V0.5 End-to-end lab test — not yet authorized for flashing

## Status
The firmware now includes a bounded in-memory queue, HTTPS POST with a
configured PEM CA certificate, bearer token, and retry/backoff. It calls
`gateway_cloud::begin()` after Wi-Fi initialization and services the queue
from the main loop. Compilation and physical validation are pending.

## Important caveats
- Current Cloud Run requires Google IAM authentication: the Heltec will get
  403 even with the correct application Bearer token until a device-facing
  ingress policy is approved and deployed.
- Opening `roles/run.invoker` to `allUsers` on the existing Cloud Run service
  would expose the endpoint publicly, with application Bearer protection on
  POST. **Do not do this without explicit owner approval.**
- HTTPS certificate validation requires provisioning the correct trusted CA
  PEM. Never disable certificate verification. A CA PEM can be entered via
  the LAB setup AP at `http://192.168.4.1/cloud` while AP mode is active.
- The setup AP currently uses a shared laboratory password. Provision secrets
  only on a trusted local network and rotate the AP password before deployment.
- Queue is RAM-only and drops newest samples when full; reboot loses pending
  samples. Upload can block the main loop for up to several seconds; radio
  responsiveness must be validated before production. No claim of full
  nonblocking delivery is made.
- A 202 HTTP response is treated as acknowledgement. This is at-least-once
  delivery; BigQuery insert IDs are best-effort, not strict uniqueness.
- Timestamp depends on ESP32 clock synchronization. Add explicit SNTP startup
  before live test, otherwise samples will be skipped.
- The provisioning portal saves credentials in ESP32 NVS, not in GitHub.

## Next gates
1. GitHub Actions Wi-Fi build green.
2. Add explicit SNTP time synchronization and test time validation.
3. Review IAM policy and secure public ingress option with owner.
4. Test Cloud Run using a fresh token over HTTPS.
5. Flash lab Heltec, provision endpoint/token/CA, check serial output.
6. Confirm new `event_id` and actual GAT562 voltage/temperature in BigQuery.
