"""MQTT JSON -> authenticated ingestion API; manual ACK only after HTTP 202.

Run from repository root: python cloud/mqtt_bridge.py profiles.json
"""
import json
import logging
import os
import sys
import urllib.request
from telemetry import from_mqtt


def forward(raw, profiles, endpoint, token):
    row = from_mqtt(json.loads(raw), profiles)
    # received_at is assigned by the ingestion service, not by the broker.
    row.pop("received_at", None)
    req = urllib.request.Request(endpoint, data=json.dumps(row, allow_nan=False).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=10) as response:
        if response.status != 202:
            raise RuntimeError("ingestion did not acknowledge event")


def main():
    import paho.mqtt.client as mqtt
    profiles = json.load(open(sys.argv[1]))
    endpoint, token = os.environ["INGEST_URL"], os.environ["INGEST_TOKEN"]
    if not endpoint.startswith("https://"):
        raise ValueError("INGEST_URL requires HTTPS")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id=os.environ["MQTT_CLIENT_ID"], clean_session=False,
                         manual_ack=True)
    client.tls_set(ca_certs=os.environ.get("MQTT_CA"))
    if os.environ.get("MQTT_USERNAME"):
        client.username_pw_set(os.environ["MQTT_USERNAME"], os.environ["MQTT_PASSWORD"])

    def connected(c, userdata, flags, reason_code, properties):
        if reason_code == 0:
            c.subscribe(os.environ["MQTT_TOPIC"], qos=1)

    def message(c, userdata, msg):
        try:
            forward(msg.payload, profiles, endpoint, token)
        except Exception:
            # Stop to allow supervisor restart and persistent-session redelivery.
            # Invalid messages also stop the bridge: operator must quarantine them.
            logging.error("Telemetry rejected or unavailable; event not acknowledged")
            c.disconnect()
            return
        c.ack(msg.mid, msg.qos)

    client.on_connect, client.on_message = connected, message
    client.connect(os.environ["MQTT_HOST"], int(os.environ.get("MQTT_PORT", "8883")))
    client.loop_forever()
    raise SystemExit(1)  # supervisor restarts after a failed/unacknowledged delivery


if __name__ == "__main__":
    main()
