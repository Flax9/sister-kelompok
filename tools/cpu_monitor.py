#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CPU Monitor (Blok E) — catat beban CPU proses server/broker tiap N detik.

Contoh:
  # REST server (cari proses python yang cmdline-nya mengandung server.py)
  python tools/cpu_monitor.py --match server.py --run-id E_rest_c2_r01
  # Broker Mosquitto lokal
  python tools/cpu_monitor.py --match mosquitto --run-id E_mqtt_c2_r01

Output: logs/<run-id>/cpu_<label>.csv
Kolom : timestamp_iso, t_ms, pid, proc_cpu_percent, proc_rss_mb, system_cpu_percent
Catatan: proc_cpu_percent dinormalisasi ke jumlah core (0–100%).
"""

import os
import sys
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psutil
from common.csvlog import CsvLogger, add_log_args, now_ms, iso_now, _safe


def find_process(match, pid):
    if pid:
        return psutil.Process(pid)
    me = os.getpid()
    candidates = []
    for p in psutil.process_iter(["pid", "name", "cmdline", "memory_info"]):
        if p.info["pid"] == me or not p.info["memory_info"]:
            continue
        text = " ".join([p.info["name"] or ""] + (p.info["cmdline"] or []))
        if match.lower() in text.lower() and "cpu_monitor" not in text:
            candidates.append(p)
    # Di Windows, python.exe dari venv adalah launcher yang membuat proses anak;
    # pilih proses dengan memori terbesar (= interpreter yang benar-benar bekerja).
    return max(candidates, key=lambda p: p.info["memory_info"].rss, default=None)


def main():
    ap = argparse.ArgumentParser(description="Monitor CPU proses server/broker")
    ap.add_argument("--match", default="server.py", help="Substring nama/cmdline proses (default: %(default)s)")
    ap.add_argument("--pid", type=int, default=None, help="PID proses (mengabaikan --match)")
    ap.add_argument("--label", default=None, help="Label file output (default: dari --match)")
    ap.add_argument("--interval", type=float, default=1.0, help="Interval sampling (detik)")
    ap.add_argument("--duration", type=float, default=None, help="Lama monitoring (detik)")
    add_log_args(ap)
    args = ap.parse_args()

    proc = find_process(args.match, args.pid)
    if not proc:
        print(f"Proses yang cocok dengan '{args.match}' tidak ditemukan. Jalankan server/broker dulu.")
        sys.exit(1)

    label = args.label or args.match
    path = os.path.join(args.log_dir, _safe(args.run_id), f"cpu_{_safe(label)}.csv")
    log = CsvLogger(path, ["timestamp_iso", "t_ms", "pid", "proc_cpu_percent",
                           "proc_rss_mb", "system_cpu_percent"])
    ncpu = psutil.cpu_count() or 1
    print(f"Memantau PID {proc.pid} ({proc.name()}) tiap {args.interval}s -> {path}")
    print("Ctrl+C untuk berhenti.")

    proc.cpu_percent(None)
    psutil.cpu_percent(None)
    start = time.monotonic()
    samples = []
    try:
        while True:
            time.sleep(args.interval)
            cpu = proc.cpu_percent(None) / ncpu
            sys_cpu = psutil.cpu_percent(None)
            rss = proc.memory_info().rss / 1e6
            samples.append(cpu)
            log.write([iso_now(), now_ms(), proc.pid, round(cpu, 2), round(rss, 1), sys_cpu])
            print(f"CPU proses={cpu:5.1f}%  | sistem={sys_cpu:5.1f}%  | RSS={rss:6.1f} MB", end="\r")
            if args.duration and time.monotonic() - start >= args.duration:
                break
    except (KeyboardInterrupt, psutil.NoSuchProcess):
        pass
    finally:
        log.close()
        if samples:
            samples.sort()
            print(f"\nSelesai. Sampel={len(samples)} | median CPU={samples[len(samples)//2]:.1f}% | max={samples[-1]:.1f}%")


if __name__ == "__main__":
    main()
