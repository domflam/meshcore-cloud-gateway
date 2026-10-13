#!/usr/bin/env python3
"""Inspect MeshCore telemetry CayenneLPP records without inventing values."""
import argparse
import json
import re

# MeshCore LPP sensor type codes. Multibyte LPP values are big-endian.
TYPES = {
    0x67: ("temperature_c", 2, 0.1, True),
    0x68: ("humidity_pct", 1, 0.5, False),
    0x73: ("barometer_hpa", 2, 0.1, False),
    0x74: ("voltage_v", 2, 0.01, False),
    0x78: ("percentage_pct", 1, 1, False),
}


def inspect(hex_payload: str) -> dict:
    clean = re.sub(r"\s+", "", hex_payload).lower()
    if len(clean) % 2 or not re.fullmatch(r"[0-9a-f]*", clean):
        raise ValueError("Payload must contain an even number of hexadecimal digits")
    raw = bytes.fromhex(clean)
    points = []
    offset = 0
    while offset + 2 <= len(raw):
        channel, sensor_type = raw[offset:offset + 2]
        if sensor_type not in TYPES:
            break  # Preserve unknown suffix rather than guessing record length.
        name, size, scale, signed = TYPES[sensor_type]
        if offset + 2 + size > len(raw):
            break
        number = int.from_bytes(raw[offset + 2:offset + 2 + size],
                                "big", signed=signed)
        points.append({"channel": channel, "type": name,
                       "value": round(number * scale, 3)})
        offset += 2 + size
    return {
        "length_bytes": len(raw),
        "hex": raw.hex(),
        "data_points": points,
        "unparsed_suffix_hex": raw[offset:].hex(),
        "note": "Battery percentage is app-derived; no percentage inferred from voltage.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", help="Hex payload after payload= in [GATEWAY] RX log")
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.payload), indent=2))
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
