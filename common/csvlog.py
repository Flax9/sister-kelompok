# -*- coding: utf-8 -*-
"""
Logger CSV thread-safe dengan skema LKM.

8 kolom inti (urutan sesuai LKM) selalu di depan; kolom tambahan
(status, rtt_ms, consumer_id, ...) diletakkan di belakang.

Struktur file: <log_dir>/<run_id>/<protocol>_<role>_<name>.csv
  role = send (pengirim) | recv (penerima) | poll (konsumen polling)
"""

import os
import csv
import re
import time
import threading
from datetime import datetime, timezone

from .config import DEFAULT_LOG_DIR

CORE_HEADERS = [
    "timestamp_iso",
    "node_id",
    "protocol",
    "t_send_ms",
    "t_recv_ms",
    "payload_bytes",
    "suhu",
    "sequence_no",
]

SEND_EXTRA = ["status", "rtt_ms", "error"]
RECV_EXTRA = ["consumer_id", "qos", "dup"]


def now_ms():
    return int(time.time() * 1000)


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def _safe(name):
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(name)).strip("-") or "x"


def add_log_args(parser, default_run_id="adhoc"):
    g = parser.add_argument_group("logging")
    g.add_argument("--log", default=None,
                   help="Path file CSV langsung (contoh: logs/A_rest.csv, menimpa --run-id)")
    g.add_argument("--run-id", default=default_run_id,
                   help="ID run, mis. B_N2_r01 (default: %(default)s). "
                        "Gunakan ID yang SAMA di semua laptop untuk satu run.")
    g.add_argument("--log-dir", default=DEFAULT_LOG_DIR, help="Folder log (default: %(default)s)")
    g.add_argument("--no-log", action="store_true", help="Jangan tulis log CSV")
    return parser


class CsvLogger:
    """Menulis baris CSV secara aman dari banyak thread, flush tiap baris."""

    def __init__(self, path, headers):
        self.path = path
        self.headers = list(headers)
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        new_file = not os.path.exists(path) or os.path.getsize(path) == 0
        self._f = open(path, mode="a", newline="", encoding="utf-8")
        self._w = csv.writer(self._f)
        if new_file:
            self._w.writerow(self.headers)
            self._f.flush()

    def write(self, row):
        if isinstance(row, dict):
            row = [row.get(h, "") for h in self.headers]
        with self._lock:
            self._w.writerow(row)
            self._f.flush()

    def close(self):
        with self._lock:
            if not self._f.closed:
                self._f.close()


class NullLogger:
    path = "(log dinonaktifkan)"

    def write(self, row):
        pass

    def close(self):
        pass


def open_logger(args, protocol, role, name, extra_headers):
    """Buat logger sesuai argumen --log / --run-id / --log-dir / --no-log."""
    if getattr(args, "no_log", False):
        return NullLogger()
    direct_log = getattr(args, "log", None)
    if direct_log:
        path = direct_log
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path)
    else:
        path = os.path.join(args.log_dir, _safe(args.run_id),
                            "%s_%s_%s.csv" % (protocol, role, _safe(name)))
    return CsvLogger(path, CORE_HEADERS + list(extra_headers))
