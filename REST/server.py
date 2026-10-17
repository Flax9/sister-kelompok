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
from common.csvlog import add_log_args, open_logger, now_ms, iso_now, RECV_EXTRA, CORE_HEADERS, CsvLogger, _safe

app = Flask(__name__)

# Diisi saat start di __main__
LOG = None
QUIET = False
ARGS = None
LATEST = {}               # node_id -> record terbaru
LATEST_LOCK = threading.Lock()
POLLER_LOGGERS = {}       # consumer_id -> CsvLogger
POLLER_LAST_SEQS = {}     # consumer_id -> {node_id: last_seq}
POLLER_LOCK = threading.Lock()


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
    t_recv_ms = now_ms()
    iso_ts = iso_now()

    # Identifikasi konsumen pemanggil (dari query, header, atau mapping IP)
    cid = request.args.get("consumer_id") or request.headers.get("X-Consumer-Id")
    if not cid:
        client_ip = request.remote_addr or "127.0.0.1"
        if client_ip.endswith(".196") or "laptop2" in client_ip:
            cid = "poll1"
        elif client_ip.endswith(".207") or "laptop3" in client_ip:
            cid = "poll2"
        elif client_ip.endswith(".10") or "laptop4" in client_ip:
            cid = "poll3"
        elif client_ip in ["127.0.0.1", "localhost"]:
            cid = "poll1"
        else:
            cid = f"poll_{client_ip.replace('.', '_')}"

    with LATEST_LOCK:
        nodes = list(LATEST.values())

    # Catat otomatis data polling ke file CSV konsumen di laptop server
    if ARGS and not getattr(ARGS, "no_log", False):
        run_id = getattr(ARGS, "run_id", "adhoc")
        log_dir = getattr(ARGS, "log_dir", "logs")
        with POLLER_LOCK:
            if cid not in POLLER_LOGGERS:
                log_path = os.path.join(log_dir, _safe(run_id), f"rest_recv_{_safe(cid)}.csv")
                POLLER_LOGGERS[cid] = CsvLogger(log_path, CORE_HEADERS + RECV_EXTRA)
                POLLER_LAST_SEQS[cid] = {}
                print(f"[REST Server] Terhubung konsumen baru: {cid} -> {log_path}")

            logger = POLLER_LOGGERS[cid]
            last_seqs = POLLER_LAST_SEQS[cid]

            for rec in nodes:
                nid = str(rec.get("node_id"))
                seq = int(rec.get("sequence_no", 0))
                if last_seqs.get(nid) == seq:
                    continue  # Belum ada data baru dari node ini
                last_seqs[nid] = seq
                t_send = int(rec.get("t_send_ms", 0))
                suhu = rec.get("suhu", 0.0)
                lat = t_recv_ms - t_send
                logger.write([iso_ts, nid, "rest", t_send, t_recv_ms, 83, suhu, seq, cid, "", ""])
                if not QUIET:
                    print(f"[REST Poller Recv] Konsumen={cid} | Node={nid} | Seq={seq:04d} | Latency={lat}ms")

    return jsonify({"server_time_ms": t_recv_ms, "nodes": nodes}), 200


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

    ARGS = args
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
        with POLLER_LOCK:
            for l in POLLER_LOGGERS.values():
                l.close()
