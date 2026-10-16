#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REST Server - Sensor Suhu Terdistribusi
Mencatat data suhu yang dikirim client dan menulis log CSV sesuai skema LKM:
timestamp_iso, node_id, protocol, t_send_ms, t_recv_ms, payload_bytes, suhu, sequence_no
(+ kolom tambahan: consumer_id, qos, dup — consumer_id = "server", qos/dup kosong)

Endpoint:
  POST /sensor  : terima data dari client (pengirim)
  GET  /latest  : data terbaru per node, untuk konsumen polling (Blok E)
  GET  /health  : cek status server

File log: logs/<run-id>/rest_recv_server.csv
"""

import os
import sys
import logging
import argparse
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from common.csvlog import add_log_args, open_logger, now_ms, iso_now, RECV_EXTRA

app = Flask(__name__)

# Diisi saat start di __main__
LOG = None
QUIET = False
LATEST = {}               # node_id -> record terbaru
LATEST_LOCK = threading.Lock()


@app.route("/sensor", methods=["POST"])
def receive_sensor():
    # Catat t_recv segera saat request tiba di server (epoch ms)
    t_recv_ms = now_ms()
    timestamp_iso = iso_now()

    payload_bytes = len(request.get_data())
    data = request.get_json(silent=True) or request.form.to_dict()

    if not data:
        return jsonify({"error": "Data payload kosong"}), 400

    try:
        node_id = str(data.get("node_id", "unknown_node"))
        t_send_ms = int(data.get("t_send_ms", 0))
        suhu = float(data.get("suhu", 0.0))
        sequence_no = int(data.get("sequence_no", 0))

        # Tulis ke file log CSV
        LOG.write([timestamp_iso, node_id, "rest", t_send_ms, t_recv_ms, payload_bytes,
                   suhu, sequence_no, "server", "", ""])

        with LATEST_LOCK:
            LATEST[node_id] = {
                "node_id": node_id,
                "t_send_ms": t_send_ms,
                "t_server_ms": t_recv_ms,
                "suhu": suhu,
                "sequence_no": sequence_no,
            }

        if not QUIET:
            latensi_ms = t_recv_ms - t_send_ms
            print(f"[REST Server] Recv: Seq={sequence_no:04d} | Node={node_id} | Suhu={suhu:.2f}°C | Latency={latensi_ms}ms")

        return jsonify({
            "status": "success",
            "sequence_no": sequence_no,
            "t_recv_ms": t_recv_ms
        }), 200

    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Format data tidak valid: {e}"}), 400


@app.route("/latest", methods=["GET"])
def latest():
    """Data terbaru semua node — dipakai REST/poller.py (konsumen polling)."""
    with LATEST_LOCK:
        nodes = list(LATEST.values())
    return jsonify({"server_time_ms": now_ms(), "nodes": nodes}), 200


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "running", "protocol": "rest"}), 200


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="REST Server Sensor Suhu")
    parser.add_argument("--host", default="0.0.0.0", help="Alamat bind (default: %(default)s)")
    parser.add_argument("--port", type=int, default=5151, help="Port (default: %(default)s)")
    parser.add_argument("--quiet", action="store_true", help="Jangan cetak tiap request (hemat CPU, Blok E)")
    add_log_args(parser)
    args = parser.parse_args()

    LOG = open_logger(args, "rest", "recv", "server", RECV_EXTRA)
    QUIET = args.quiet
    # Matikan log akses werkzeug per-request agar tidak membebani CPU/terminal
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    print(f"=== REST Server Sensor Suhu Aktif ===")
    print(f"Log CSV tersimpan di: {LOG.path}")
    print(f"Endpoint: http://{args.host}:{args.port}/sensor  (POST)")
    print(f"          http://{args.host}:{args.port}/latest  (GET, polling)")
    try:
        app.run(host=args.host, port=args.port, debug=False, threaded=True)
    finally:
        LOG.close()
