#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REST Poller - Konsumen/Dashboard REST (Blok E: fan-out)

Melakukan polling GET /latest secara periodik. Setiap data BARU
(node_id, sequence_no belum pernah dilihat) dicatat ke log:
  logs/<run-id>/rest_recv_<consumer_id>.csv

t_recv_ms = saat poller menerima data, sehingga latensi
(t_recv_ms - t_send_ms) mencakup jeda polling — inilah biaya model pull
dibanding push MQTT.
"""

import os
import sys
import json
import time
import socket
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from common.csvlog import add_log_args, open_logger, now_ms, iso_now, RECV_EXTRA


def run_poller(args):
    url = args.server.rstrip("/") + "/latest"
    print("=== REST Poller (Konsumen) Aktif ===")
    print(f"URL         : {url}")
    print(f"Consumer ID : {args.consumer_id}")
    print(f"Interval    : {args.interval} detik")

    log = open_logger(args, "rest", "recv", args.consumer_id, RECV_EXTRA)
    print(f"Log CSV     : {log.path}")
    print("-" * 55)

    http = requests.Session() if args.keepalive else requests
    last_seq = {}  # node_id -> sequence_no terakhir yang dicatat
    polls = new_items = errors = 0
    start = time.monotonic()

    try:
        while True:
            polls += 1
            try:
                resp = http.get(url, params={"consumer_id": args.consumer_id},
                                headers={"X-Consumer-Id": args.consumer_id},
                                timeout=args.timeout)
                t_recv_ms = now_ms()
                body = resp.content
                data = json.loads(body)
                nodes = data.get("nodes", [])
                for rec in nodes:
                    node_id = str(rec.get("node_id"))
                    seq = int(rec.get("sequence_no", 0))
                    if last_seq.get(node_id) == seq:
                        continue  # belum ada data baru dari node ini
                    last_seq[node_id] = seq
                    new_items += 1
                    t_send_ms = int(rec.get("t_send_ms", 0))
                    log.write([iso_now(), node_id, "rest", t_send_ms, t_recv_ms,
                               len(body) // max(len(nodes), 1),
                               rec.get("suhu", ""), seq, args.consumer_id, "", ""])
                    if not args.quiet:
                        print(f"[REST Poll] New: Node={node_id} | Seq={seq:04d} | Latency={t_recv_ms - t_send_ms}ms")
            except (requests.exceptions.RequestException, ValueError) as e:
                errors += 1
                print(f"[REST Poll] Gagal polling: {type(e).__name__}")

            if args.duration and time.monotonic() - start >= args.duration:
                break
            next_at = start + polls * args.interval
            time.sleep(max(0.0, next_at - time.monotonic()))

    except KeyboardInterrupt:
        pass
    finally:
        log.close()
        print(f"\n[REST Poll] Selesai. Poll={polls} | Data baru={new_items} | Error={errors}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="REST Poller (konsumen dashboard)")
    parser.add_argument("--server", default="http://127.0.0.1:5151", help="Base URL server REST")
    parser.add_argument("--consumer-id", default=f"poller-{socket.gethostname()}", help="ID konsumen")
    parser.add_argument("--interval", type=float, default=1.0, help="Interval polling (detik)")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout request (detik)")
    parser.add_argument("--duration", type=float, default=None, help="Lama polling (detik), default tanpa batas")
    parser.add_argument("--keepalive", action="store_true", help="Pakai koneksi HTTP persisten")
    parser.add_argument("--quiet", action="store_true", help="Jangan cetak tiap data")
    add_log_args(parser)
    run_poller(parser.parse_args())
