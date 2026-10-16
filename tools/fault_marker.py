#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fault Marker (Blok D) — pencatat waktu putus/pulih jaringan.

Jalankan di laptop pengirim bersamaan dengan pub.py / client.py:
  python tools/fault_marker.py --protocol mqtt --run-id D_mqtt_r01

Tekan ENTER tepat saat mematikan Wi-Fi  -> event "putus"
Tekan ENTER lagi saat Wi-Fi menyala     -> event "pulih"
Ketik q lalu ENTER untuk selesai.

Output: logs/<run-id>/fault_<protocol>.csv
Kolom : timestamp_iso, t_ms, protocol, event, outage_no
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.csvlog import CsvLogger, add_log_args, now_ms, iso_now, _safe


def main():
    ap = argparse.ArgumentParser(description="Pencatat waktu putus/pulih (Blok D)")
    ap.add_argument("--protocol", required=True, choices=["mqtt", "rest"])
    add_log_args(ap)
    args = ap.parse_args()

    path = os.path.join(args.log_dir, _safe(args.run_id), f"fault_{args.protocol}.csv")
    log = CsvLogger(path, ["timestamp_iso", "t_ms", "protocol", "event", "outage_no"])
    print(f"Log: {path}")
    print("ENTER = tandai putus/pulih bergantian | q + ENTER = selesai\n")

    outage, down = 0, False
    t_down = None
    try:
        while True:
            cmd = input("[putus]" if not down else "[pulih]").strip().lower()
            if cmd == "q":
                break
            t = now_ms()
            if not down:
                outage += 1
                t_down = t
                log.write([iso_now(), t, args.protocol, "putus", outage])
                print(f"  #{outage} PUTUS dicatat")
            else:
                log.write([iso_now(), t, args.protocol, "pulih", outage])
                print(f"  #{outage} PULIH dicatat (durasi {(t - t_down) / 1000:.1f} s)")
            down = not down
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        log.close()


if __name__ == "__main__":
    main()
