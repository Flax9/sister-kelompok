#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT Publisher - Node Sensor Suhu Terdistribusi
Mengirimkan data suhu periodik ke Broker MQTT dengan payload JSON:
{
    "node_id": str,
    "t_send_ms": int,
    "suhu": float,
    "sequence_no": int
}

Setiap pesan juga dicatat di log pengirim:
  logs/<run-id>/mqtt_send_<node_id>.csv
  (8 kolom inti LKM + status, rtt_ms, error)

Konfigurasi broker dibaca dari MQTT/.env (lihat MQTT/.env.example).
"""

import os
import sys
import json
import time
import socket
import random
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paho.mqtt.client as mqtt
from common.config import add_mqtt_args, apply_mqtt_connection
from common.csvlog import add_log_args, open_logger, now_ms, iso_now, SEND_EXTRA


def ts():
    return time.strftime("%H:%M:%S")


def run_publisher(args):
    print("=== MQTT Publisher Sensor Suhu Aktif ===")
    print(f"Broker Host   : {args.broker}:{args.port} (TLS: {args.tls})")
    print(f"Topik Target  : {args.topic}")
    print(f"Node ID       : {args.node_id}")
    print(f"Client ID     : {args.client_id} (sesi persisten: {args.persistent})")
    print(f"QoS           : {args.qos}")
    print(f"Interval      : {args.interval} detik")
    print(f"Target Jumlah : {'Selamanya (Ctrl+C untuk stop)' if args.count is None else f'{args.count} pesan'}")

    log = open_logger(args, "mqtt", "send", args.node_id, SEND_EXTRA)
    print(f"Log pengirim  : {log.path}")
    print("-" * 55)

    state = {"fatal": None}

    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code.is_failure:
            # Jangan sys.exit() di sini: callback berjalan di thread jaringan.
            state["fatal"] = f"Gagal terhubung ke broker: {reason_code}"
            client.disconnect()
        else:
            print(f"[{ts()}] Terhubung ke broker {args.broker} (session_present={flags.session_present})")

    def on_disconnect(client, userdata, flags, reason_code, properties=None):
        print(f"[{ts()}] Terputus dari broker ({reason_code}). paho akan reconnect otomatis...")

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=args.client_id,
        clean_session=not args.persistent,
        protocol=mqtt.MQTTv311,
    )
    apply_mqtt_connection(client, args)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    try:
        print(f"Menghubungkan ke {args.broker}:{args.port}...")
        client.connect(args.broker, args.port, keepalive=args.keepalive)
        client.loop_start()
    except Exception as e:
        print(f"Gagal menghubungkan ke broker: {e}")
        log.close()
        sys.exit(1)

    # Tunggu koneksi pertama (maks 10 detik) agar pesan awal tidak langsung gagal
    deadline = time.time() + 10
    while not client.is_connected() and time.time() < deadline and not state["fatal"]:
        time.sleep(0.05)
    if state["fatal"]:
        print(state["fatal"])
        client.loop_stop()
        log.close()
        sys.exit(1)

    sequence_no = 0
    start = time.monotonic()
    try:
        while True:
            if state["fatal"]:
                print(state["fatal"])
                break

            sequence_no += 1
            t_send_ms = now_ms()
            suhu = round(random.uniform(25.0, 32.0), 2)

            payload_dict = {
                "node_id": args.node_id,
                "t_send_ms": t_send_ms,
                "suhu": suhu,
                "sequence_no": sequence_no,
            }
            payload_str = json.dumps(payload_dict)
            payload_bytes = len(payload_str.encode("utf-8"))

            # Tidak memakai wait_for_publish() agar jadwal kirim tidak molor.
            # Saat terputus: QoS 0 -> gagal; QoS 1/2 -> diantrikan paho & dikirim ulang saat pulih.
            info = client.publish(args.topic, payload_str, qos=args.qos)
            if info.rc == mqtt.MQTT_ERR_SUCCESS:
                status, err = "ok", ""
            elif args.qos > 0 and info.rc == mqtt.MQTT_ERR_NO_CONN:
                status, err = "queued", mqtt.error_string(info.rc)
            else:
                status, err = "fail", mqtt.error_string(info.rc)

            log.write([iso_now(), args.node_id, "mqtt", t_send_ms, "", payload_bytes,
                       suhu, sequence_no, status, "", err])

            print(f"[MQTT Pub] Sent: Seq={sequence_no:04d} | Suhu={suhu:.2f}°C | Bytes={payload_bytes} | QoS={args.qos} | {status}")

            if args.count is not None and sequence_no >= args.count:
                print(f"Selesai mengirim {args.count} pesan.")
                time.sleep(1.0)  # beri waktu pesan terakhir terkirim
                break

            # Jadwal berbasis waktu absolut: kirim ke-n terjadi pada start + n*interval
            next_at = start + sequence_no * args.interval
            time.sleep(max(0.0, next_at - time.monotonic()))

    except KeyboardInterrupt:
        print(f"\n[MQTT Pub] Dihentikan oleh pengguna. Total terkirim: {sequence_no} pesan.")
    finally:
        client.loop_stop()
        client.disconnect()
        log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MQTT Publisher Sensor Suhu")
    add_mqtt_args(parser)
    parser.add_argument("--node-id", default=socket.gethostname(), help="ID unik node pengirim")
    parser.add_argument("--client-id", default=None, help="Client ID MQTT (default: pub-<node_id>)")
    parser.add_argument("--persistent", action="store_true",
                        help="Sesi persisten (clean_session=False), untuk Blok D/F")
    parser.add_argument("--interval", type=float, default=1.0, help="Interval pengiriman dalam detik")
    parser.add_argument("--qos", type=int, default=0, choices=[0, 1, 2], help="Tingkat QoS MQTT (0, 1, 2)")
    parser.add_argument("--count", type=int, default=None, help="Jumlah pesan yang dikirim (default: None)")
    parser.add_argument("--keepalive", type=int, default=60, help="Keepalive MQTT (detik)")
    add_log_args(parser)

    args = parser.parse_args()
    args.client_id = args.client_id or (f"pub-{args.node_id}" if args.persistent else f"pub-{args.node_id}-{os.getpid()}")
    run_publisher(args)
