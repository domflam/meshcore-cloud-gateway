#pragma once

// Copy to gateway.local.h (gitignored), then replace the example with the FULL
// 64-character public key exported from a repeater contact in the mobile app.
// Add up to eight keys, separated by commas. These are not private identity keys.
#define GATEWAY_TARGET_KEYS { \
  "REPLACE_WITH_64_HEXADECIMAL_CHARACTERS" \
}
#define GATEWAY_INTERVAL_MS 900000UL
