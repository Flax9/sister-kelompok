#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT Subscriber - Konsumen Data Sensor Suhu Terdistribusi
Menerima pesan dari topic MQTT dan menulis log CSV sesuai skema LKM:
timestamp_iso, node_id, protocol, t_send_ms, t_recv_ms, payload_bytes, suhu, sequence_no
(+ kolom tambahan: consumer_id, qos, dup)

File log: logs/<run-id>/mqtt_recv_<consumer_id>.csv
Beberapa subscriber (Blok E) cukup diberi --consumer-id berbeda.
"""

import os
import sys
import json
import time
import socket
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paho.mqtt.client as mqtt
from common.config import add_mqtt_args, apply_mqtt_connection
from common.csvlog import add_log_args, open_logger, now_ms, iso_now, RECV_EXTRA


def ts():
    return time.strftime("%H:%M:%S")


def run_subscriber(args):
    print("=== MQTT Subscriber Sensor Suhu Aktif ===")
    print(f"Broker Host : {args.broker}:{args.port} (TLS: {args.tls})")
    print(f"Topik       : {args.topic}")
    print(f"QoS Target  : {args.qos}")
    print(f"Consumer ID : {args.consumer_id}")
    print(f"Client ID   : {args.client_id} (sesi persisten: {args.persistent})")

    log = open_logger(args, "mqtt", "recv", args.consumer_id, RECV_EXTRA)
    print(f"Log CSV     : {log.path}")
    print("-" * 55)

    state = {"fatal": None, "count": 0}

    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code.is_failure:
            # Jangan sys.exit() di callback; hentikan loop dengan disconnect.
            state["fatal"] = f"Gagal terhubung ke broker: {reason_code}"
            client.disconnect()
            return
        print(f"[{ts()}] Terhubung ke broker {args.broker} (session_present={flags.session_present})")
        client.subscribe(args.topic, qos=args.qos)
        print(f"Berlangganan topik: {args.topic} (QoS: {args.qos})")
        print("Menunggu data sensor... (Tekan Ctrl+C untuk berhenti)\n")

    def on_disconnect(client, userdata, flags, reason_code, properties=None):
        if not state["fatal"]:
            print(f"[{ts()}] Terputus dari broker ({reason_code}). Reconnect otomatis...")

    def on_message(client, userdata, message):
        # Catat t_recv_ms segera saat pesan diterima (epoch ms)
        t_recv_ms = now_ms()
        timestamp_iso = iso_now()
        payload_bytes = len(message.payload)

        try:
            data = json.loads(message.payload.decode("utf-8"))

            node_id = str(data.get("node_id", "unknown"))
            t_send_ms = int(data.get("t_send_ms", 0))
            suhu = float(data.get("suhu", 0.0))
            sequence_no = int(data.get("sequence_no", 0))

            log.write([timestamp_iso, node_id, "mqtt", t_send_ms, t_recv_ms, payload_bytes,
                       suhu, sequence_no, args.consumer_id, message.qos, int(message.dup)])
            state["count"] += 1

            latensi_ms = t_recv_ms - t_send_ms
            print(f"[MQTT Sub] Recv: Seq={sequence_no:04d} | Node={node_id} | Suhu={suhu:.2f}°C | Bytes={payload_bytes} | Latency={latensi_ms}ms")

        except Exception as e:
            print(f"[MQTT Sub] Format pesan tidak valid ({e}): {message.payload!r}")

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=args.client_id,
        clean_session=not args.persistent,
        protocol=mqtt.MQTTv311,
    )
    apply_mqtt_connection(client, args)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        print(f"Menghubungkan ke {args.broker}:{args.port}...")
        client.connect(args.broker, args.port, keepalive=args.keepalive)
        client.loop_forever(retry_first_connection=True)
    except KeyboardInterrupt:
        print(f"\n[MQTT Sub] Dihentikan oleh pengguna. Total diterima: {state['count']} pesan.")
    except Exception as e:
        print(f"Gagal menghubungkan ke broker: {e}")
    finally:
        client.disconnect()
        log.close()
        if state["fatal"]:
            print(state["fatal"])
            sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MQTT Subscriber Sensor Suhu")
    add_mqtt_args(parser)
    parser.add_argument("--qos", type=int, default=0, choices=[0, 1, 2], help="Tingkat QoS MQTT (0, 1, 2)")
    parser.add_argument("--consumer-id", default=socket.gethostname(), help="ID konsumen (Blok E)")
    parser.add_argument("--client-id", default=None, help="Client ID MQTT (default: sub-<consumer_id>)")
    parser.add_argument("--persistent", action="store_true",
                        help="Sesi persisten (clean_session=False), untuk Blok D/F")
    parser.add_argument("--keepalive", type=int, default=60, help="Keepalive MQTT (detik)")
    add_log_args(parser)

    args = parser.parse_args()
    args.client_id = args.client_id or f"sub-{args.consumer_id}"
    run_subscriber(args)