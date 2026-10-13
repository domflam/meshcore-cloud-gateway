#!/usr/bin/env python3
"""Inspect captured MeshCore telemetry payloads without guessing sensor semantics.

Usage:
    python3 tools/inspect_telemetry.py 0174019b016700d400000000
"""
import argparse
import json
import re


def inspect(hex_payload: str) -> dict:
    clean = re.sub(r"\s+", "", hex_payload).lower()
    if len(clean) % 2 or not re.fullmatch(r"[0-9a-f]*", clean):
        raise ValueError("Payload must contain an even number of hexadecimal digits")
    raw = bytes.fromhex(clean)
    return {
        "length_bytes": len(raw),
        "hex": raw.hex(),
        "octets": [f"{b:02x}" for b in raw],
        # Diagnostic interpretations only; NOT identified MeshCore fields.
        "uint16_be_candidates": [
            int.from_bytes(raw[i:i + 2], "big") for i in range(0, len(raw) - 1, 2)
        ],
        "uint16_le_candidates": [
            int.from_bytes(raw[i:i + 2], "little") for i in range(0, len(raw) - 1, 2)
        ],
        "interpretation": "unknown: confirm MeshCore telemetry schema before assigning sensor fields",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", help="Hex payload after 'payload=' in [GATEWAY] RX log")
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.payload), indent=2))
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
