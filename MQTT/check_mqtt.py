#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Pengecekan Koneksi MQTT (sesuai JOBDESK.md).
Memverifikasi koneksi ke broker EMQX/HiveMQ dari konfigurasi MQTT/.env.
"""

import os
import sys
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paho.mqtt.client as mqtt
from common.config import mqtt_settings, apply_mqtt_connection


def main():
    s = mqtt_settings()
    print("=== Pengecekan Koneksi MQTT ===")
    print(f"Broker Host : {s['broker']}:{s['port']} (TLS: {s['tls']})")
    print(f"Username    : {s['username'] or '(tanpa username)'}")
    print(f"Topik       : {s['topic']}")
    print(f"Sumber env  : {s['source']}")
    print("-" * 50)

    if not s["username"] or not s["password"]:
        print("[PERINGATAN] Username/Password belum diisi di MQTT/.env!")

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="check-" + str(int(time.time())),
        protocol=mqtt.MQTTv311,
    )

    class Args:
        username = s["username"]
        password = s["password"]
        tls = s["tls"]
        ca_cert = s["ca_cert"]

    apply_mqtt_connection(client, Args)

    received = {"status": False, "msg": None}

    def on_connect(c, userdata, flags, rc, properties=None):
        if not rc.is_failure:
            print(f"[OK] Berhasil terhubung ke broker ({s['broker']})")
            c.subscribe(s["topic"] + "/check", qos=1)
            c.publish(s["topic"] + "/check", "ping_test", qos=1)
        else:
            print(f"[GAGAL] Error saat koneksi: {rc}")

    def on_message(c, userdata, msg):
        received["status"] = True
        received["msg"] = msg.payload.decode("utf-8", errors="ignore")

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Menghubungkan ke {s['broker']}:{s['port']}...")
    try:
        client.connect(s["broker"], s["port"], keepalive=30)
        client.loop_start()

        timeout = time.time() + 8.0
        while time.time() < timeout and not received["status"]:
            time.sleep(0.1)

        client.loop_stop()
        client.disconnect()

        if received["status"]:
            print(f"[OK] Berhasil publish dan subscribe pesan uji: '{received['msg']}'")
            print("\n>>> HASIL: SUKSES <<<")
            sys.exit(0)
        else:
            print("\n>>> HASIL: GAGAL (Koneksi timeout atau pesan tidak diterima) <<<")
            sys.exit(1)

    except Exception as e:
        print(f"[ERROR] Exception saat menghubungkan: {e}")
        print("\n>>> HASIL: GAGAL <<<")
        sys.exit(1)


if __name__ == "__main__":
    main()
