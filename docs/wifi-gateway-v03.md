# V0.3 — Wi-Fi-only gateway laboratory build

Goal: compile the **official MeshCore Heltec V3 Wi-Fi Companion** with the
previously validated autonomous GAT562 polling and CayenneLPP decoder.

- The V0.2 BLE firmware remains the recovery baseline; this branch does not
  remove or alter its existing build workflow.
- New CI workflow: `.github/workflows/heltec-lab-wifi.yml`.
- Wi-Fi transport uses upstream MeshCore Companion functionality. **Cloud Run
  HTTPS uploads are not implemented yet.**
- The GAT562 contact must still exist in the device's MeshCore contact store.
  Do not assume that flashing preserves contacts or device identity.
- Wi-Fi Companion configuration and app connectivity must be validated on
  physical hardware before attempting cloud integration.
- Do not flash unless the Wi-Fi LAB build is green and the generated binary
  matches the intended flash method (merged vs app-only firmware).
- Initial acceptance: device boots, joins Wi-Fi, MeshCore Companion is usable
  over Wi-Fi, and serial logs show TX/RX and decoded voltage/temperature.

## Serial acceptance sample

```text
[GATEWAY] TX GAT562 ...
[GATEWAY] RX GAT562 telemetry ...
[GATEWAY] GAT562 voltage=4.10 V
[GATEWAY] GAT562 temperature=21.5 C
```

This is a **build-and-hardware-validation** milestone, not a cloud-ready gateway.
