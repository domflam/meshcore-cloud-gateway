"""Pure MQTT envelope adapter. Profiles are trusted local configuration."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from inspect_telemetry import inspect
from app import normalize

MEASUREMENTS = {"voltage_v", "temperature_c", "humidity_pct", "pressure_hpa", "wind_speed_mps"}


def from_mqtt(payload, profiles):
    """Accept legacy flat JSON or {metadata, lpp_hex}; never infer wind from zero."""
    if not isinstance(payload, dict):
        raise ValueError("JSON object required")
    if "lpp_hex" not in payload:
        return normalize(payload)
    if not isinstance(payload["lpp_hex"], str):
        raise ValueError("lpp_hex must be a string")
    if any(k in payload for k in MEASUREMENTS | {"wind_simulated"}):
        raise ValueError("mixed raw and normalized measurements")
    profile = profiles.get(payload.get("node_id"))
    if not isinstance(profile, dict):
        raise ValueError("raw telemetry requires a node profile")
    decoded = inspect(payload["lpp_hex"])
    # Inspector preserves suffixes for diagnosis; ingestion must not store partial data.
    suffix = decoded["unparsed_suffix_hex"]
    padding = profile.get("trailing_zero_padding_bytes", 0)
    if suffix and not (type(padding) is int and padding > 0 and suffix == "00" * padding):
        raise ValueError("unknown or truncated LPP record")
    row = {k: payload[k] for k in ("node_id", "event_id", "observed_at", "source") if k in payload}
    for point in decoded["data_points"]:
        key = f'{point["channel"]}:{point["type"]}'
        mapping = profile.get(key)
        if mapping is None:
            continue
        if not isinstance(mapping, dict) or mapping.get("field") not in MEASUREMENTS:
            raise ValueError("invalid profile mapping")
        field = mapping["field"]
        if field in row:
            raise ValueError("ambiguous duplicate measurement: " + field)
        row[field] = point["value"]
        if field == "wind_speed_mps":
            simulated = mapping.get("simulated")
            if not isinstance(simulated, bool):
                raise ValueError("wind profile requires explicit simulated boolean")
            row["wind_simulated"] = simulated
    return normalize(row)
