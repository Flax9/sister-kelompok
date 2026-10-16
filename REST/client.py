#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REST Client - Node Sensor Suhu Terdistribusi
Mengirimkan data suhu periodik ke REST Server dengan field:
node_id, t_send_ms, suhu, sequence_no

Setiap request dicatat di log pengirim:
  logs/<run-id>/rest_send_<node_id>.csv
  (8 kolom inti LKM + status, rtt_ms, error)

Default: koneksi baru per request & TANPA retry (sesuai hipotesis H3).
"""

import os
import sys
import json
import time
import socket
import random
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from common.csvlog import add_log_args, open_logger, now_ms, iso_now, SEND_EXTRA


def run_client(args):
    server_url = args.server.rstrip("/")
    if not server_url.endswith("/sensor"):
        server_url += "/sensor"

    print(f"=== REST Client Sensor Suhu Aktif ===")
    print(f"Target Server : {server_url}")
    print(f"Node ID       : {args.node_id}")
    print(f"Interval      : {args.interval} detik")
    print(f"Timeout       : {args.timeout} detik | Retry: {args.retries} | Keep-alive: {args.keepalive}")
    print(f"Target Jumlah : {'Selamanya (Ctrl+C untuk stop)' if args.count is None else f'{args.count} pesan'}")

    log = open_logger(args, "rest", "send", args.node_id, SEND_EXTRA)
    print(f"Log pengirim  : {log.path}")
    print("-" * 55)

    http = requests.Session() if args.keepalive else requests

    sequence_no = 0
    start = time.monotonic()
    try:
        while True:
            sequence_no += 1
            t_send_ms = now_ms()
            # Simulasi pembacaan suhu sensor (misal 25.0°C - 32.0°C)
            suhu = round(random.uniform(25.0, 32.0), 2)

            payload = {
                "node_id": args.node_id,
                "t_send_ms": t_send_ms,
                "suhu": suhu,
                "sequence_no": sequence_no
            }
            payload_bytes = len(json.dumps(payload).encode("utf-8"))

            status, rtt_ms, err = "fail", "", ""
            for attempt in range(args.retries + 1):
                try:
                    t_req_start = time.perf_counter()
                    response = http.post(server_url, json=payload, timeout=args.timeout)
                    rtt_ms = round((time.perf_counter() - t_req_start) * 1000, 2)

                    if response.status_code == 200:
                        status, err = "ok", ""
                        print(f"[REST Client] Sent: Seq={sequence_no:04d} | Suhu={suhu:.2f}°C | RTT={rtt_ms}ms | HTTP 200 OK")
                        break
                    status, err = f"http_{response.status_code}", response.text[:100]
                    print(f"[REST Client] Warning: Seq={sequence_no:04d} | Status={response.status_code} | Msg={response.text}")

                except requests.exceptions.RequestException as e:
                    status, rtt_ms, err = "fail", "", type(e).__name__
                    print(f"[REST Client] Gagal mengirim Seq={sequence_no:04d}: {type(e).__name__}")

            log.write([iso_now(), args.node_id, "rest", t_send_ms, "", payload_bytes,
                       suhu, sequence_no, status, rtt_ms, err])

            if args.count is not None and sequence_no >= args.count:
                print(f"Selesai mengirim {args.count} pesan.")
                break

            # Jadwal berbasis waktu absolut; jika request lambat, kirim berikutnya segera
            next_at = start + sequence_no * args.interval
            time.sleep(max(0.0, next_at - time.monotonic()))

    except KeyboardInterrupt:
        print(f"\n[REST Client] Dihentikan oleh pengguna. Total terkirim: {sequence_no} pesan.")
    finally:
        log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="REST Client Sensor Suhu")
    parser.add_argument("--server", default="http://127.0.0.1:5151/sensor", help="URL endpoint server REST (contoh: http://192.168.1.10:5151/sensor)")
    parser.add_argument("--node-id", default=socket.gethostname(), help="ID unik node pengirim (default: nama komputer)")
    parser.add_argument("--interval", type=float, default=1.0, help="Interval pengiriman dalam detik (default: 1.0)")
    parser.add_argument("--count", type=int, default=None, help="Jumlah pesan yang dikirim (default: None / terus menerus)")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout request (detik)")
    parser.add_argument("--retries", type=int, default=0, help="Jumlah retry saat gagal (default 0, sesuai H3)")
    parser.add_argument("--keepalive", action="store_true", help="Pakai koneksi HTTP persisten (requests.Session)")
    add_log_args(parser)

    args = parser.parse_args()
    run_client(args)
