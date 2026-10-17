# -*- coding: utf-8 -*-
"""
Auto Fault Injector (Blok D) — Versi Presisi Non-Admin
Memaksa Wi-Fi tetap terputus selama tepat 15 detik penuh (mencegah Windows auto-reconnect)
lalu menyambungkan kembali secara otomatis.
"""

import os
import re
import sys
import time
import subprocess
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.csvlog import CsvLogger, add_log_args, now_ms, iso_now, _safe


def get_current_wifi_profile():
    """Dapatkan nama profil/SSID Wi-Fi yang sedang aktif saat ini."""
    try:
        res = subprocess.run("netsh wlan show interfaces", shell=True, capture_output=True, text=True)
        profile_match = re.search(r"Profile\s*:\s*(.+)", res.stdout)
        if profile_match:
            return profile_match.group(1).strip()
        ssid_match = re.search(r"SSID\s*:\s*(.+)", res.stdout)
        if ssid_match:
            return ssid_match.group(1).strip()
    except Exception:
        pass
    return None


def disconnect_wifi():
    """Putuskan koneksi Wi-Fi."""
    try:
        res = subprocess.run("netsh wlan disconnect", shell=True, capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False


def reconnect_wifi(profile_name=None):
    """Sambungkan kembali ke profil Wi-Fi."""
    try:
        if profile_name:
            cmd = f'netsh wlan connect name="{profile_name}"'
        else:
            cmd = "netsh wlan connect"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description="Auto Fault Injector Wi-Fi 15s Presisi")
    ap.add_argument("--protocol", required=True, choices=["mqtt", "rest"])
    ap.add_argument("--duration", type=int, default=15, help="Durasi putus (detik, default: 15)")
    add_log_args(ap)
    args = ap.parse_args()

    active_profile = get_current_wifi_profile()

    path = os.path.join(args.log_dir, _safe(args.run_id), f"fault_{args.protocol}.csv")
    log = CsvLogger(path, ["timestamp_iso", "t_ms", "protocol", "event", "outage_no"])

    print("=" * 60)
    print(f"AUTO FAULT INJECTOR BLOK D ({args.protocol.upper()}) - EXACT TIMER")
    print(f"Profil Wi-Fi Aktif : {active_profile or 'Default profile'}")
    print(f"Durasi Gangguan    : {args.duration} detik tepat")
    print(f"Log tersimpan di   : {path}")
    print("=" * 60)
    print("Mekanisme: Memaksa disconnect kontinu selama 15 detik penuh")
    print("agar Windows tidak melakukan auto-reconnect prematur.")
    print("\nTekan [ENTER] saat Anda siap memulai simulasi...")
    print("(Ketik q lalu ENTER untuk keluar)\n")

    outage = 0
    try:
        while True:
            cmd = input(f"Run #{outage+1} Siap? [Tekan ENTER]: ").strip().lower()
            if cmd == "q":
                break

            outage += 1
            print(f"\n[#{outage}] Memutuskan koneksi Wi-Fi...")
            t_down = now_ms()
            log.write([iso_now(), t_down, args.protocol, "putus", outage])
            
            start_mono = time.monotonic()
            print(f"  >>> WAKTU PUTUS : {time.strftime('%H:%M:%S')}")

            # Loop pemutusan kontinu agar Windows tidak auto-reconnect sendiri sebelum 15 detik
            while True:
                elapsed = time.monotonic() - start_mono
                remaining = args.duration - elapsed
                if remaining <= 0:
                    break
                
                # Paksa putus setiap interval
                disconnect_wifi()
                print(f"      Wi-Fi Terputus... sisa {remaining:.1f} detik   ", end="\r")
                time.sleep(0.4)

            print(f"\n[#{outage}] Waktu gangguan 15 detik selesai. Menyambungkan kembali Wi-Fi...")
            reconnect_wifi(active_profile)
            t_up = now_ms()
            log.write([iso_now(), t_up, args.protocol, "pulih", outage])
            print(f"  >>> WAKTU PULIH : {time.strftime('%H:%M:%S')} (Durasi gangguan: {(t_up - t_down)/1000:.2f} detik)\n")
            print("-" * 55)

    except KeyboardInterrupt:
        print("\nDibatalkan oleh pengguna. Menyambungkan kembali Wi-Fi...")
        reconnect_wifi(active_profile)
    finally:
        log.close()


if __name__ == "__main__":
    main()
