# -*- coding: utf-8 -*-
"""
Auto Fault Injector (Blok D)
Mematikan dan menyalakan kembali adapter Wi-Fi Windows secara otomatis via netsh
selama 15 detik, sekaligus mencatat timestamp putus dan pulih secara presisi.

Jalankan di PowerShell (Run as Administrator jika perlu izin adapter):
  python tools/auto_fault.py --protocol rest --run-id D_rest_r01
"""

import os
import sys
import time
import subprocess
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.csvlog import CsvLogger, add_log_args, now_ms, iso_now, _safe

def toggle_wifi(enable=True, interface_name="Wi-Fi"):
    state = "enabled" if enable else "disabled"
    cmd = f'netsh interface set interface name="{interface_name}" admin={state}'
    try:
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    ap = argparse.ArgumentParser(description="Auto Fault Injector Wi-Fi 15s")
    ap.add_argument("--protocol", required=True, choices=["mqtt", "rest"])
    ap.add_argument("--duration", type=int, default=15, help="Durasi putus (detik, default: 15)")
    ap.add_argument("--interface", default="Wi-Fi", help="Nama antarmuka Wi-Fi (default: Wi-Fi)")
    add_log_args(ap)
    args = ap.parse_args()

    path = os.path.join(args.log_dir, _safe(args.run_id), f"fault_{args.protocol}.csv")
    log = CsvLogger(path, ["timestamp_iso", "t_ms", "protocol", "event", "outage_no"])

    print("=" * 60)
    print(f"AUTO FAULT INJECTOR BLOK D ({args.protocol.upper()})")
    print(f"Interface Target : {args.interface}")
    print(f"Durasi Gangguan  : {args.duration} detik")
    print(f"Log tersimpan di : {path}")
    print("=" * 60)
    print("\nTekan [ENTER] saat Anda siap memulai simulasi putus 15 detik...")
    print("(Ketik q lalu ENTER untuk keluar)\n")

    outage = 0
    try:
        while True:
            cmd = input(f"Run #{outage+1} Siap? [Tekan ENTER]: ").strip().lower()
            if cmd == "q":
                break

            outage += 1
            print(f"\n[#{outage}] Mematikan adapter {args.interface}...")
            t_down = now_ms()
            log.write([iso_now(), t_down, args.protocol, "putus", outage])
            toggle_wifi(enable=False, interface_name=args.interface)
            print(f"  >>> WAKTU PUTUS: {time.strftime('%H:%M:%S')} (Hitung mundur {args.duration}s)...")

            for remaining in range(args.duration, 0, -1):
                print(f"      Wi-Fi Mati... sisa {remaining} detik", end="\r")
                time.sleep(1)

            print(f"\n[#{outage}] Menyalakan kembali adapter {args.interface}...")
            toggle_wifi(enable=True, interface_name=args.interface)
            t_up = now_ms()
            log.write([iso_now(), t_up, args.protocol, "pulih", outage])
            print(f"  >>> WAKTU PULIH: {time.strftime('%H:%M:%S')} (Durasi: {(t_up - t_down)/1000:.1f} detik)\n")
            print("-" * 50)

    except KeyboardInterrupt:
        print("\nDibatalkan oleh pengguna. Memastikan Wi-Fi kembali aktif...")
        toggle_wifi(enable=True, interface_name=args.interface)
    finally:
        log.close()

if __name__ == "__main__":
    main()
