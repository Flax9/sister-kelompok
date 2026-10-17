# -*- coding: utf-8 -*-
"""
Dashboard Ringkasan Hasil Blok E (Fan-out Konsumen)
Membaca otomatis:
1. Beban CPU server/broker dari logs/<run-id>/cpu_*.csv
2. Latensi median dan throughput per konsumen dari logs/<run-id>/*_recv_*.csv
Mencetak langsung tabel LKM yang siap disalin!
"""

import os
import sys
import glob
import argparse
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(ROOT, "logs")

def analyze_block_e_run(run_id):
    run_dir = os.path.join(LOGS_DIR, run_id)
    if not os.path.exists(run_dir):
        print(f"Error: Folder run '{run_dir}' tidak ditemukan.")
        return

    # 1. Analisis CPU
    cpu_files = glob.glob(os.path.join(run_dir, "cpu_*.csv"))
    median_cpu = 0.0
    max_cpu = 0.0
    cpu_samples = 0
    if cpu_files:
        try:
            df_cpu = pd.read_csv(cpu_files[0])
            if "proc_cpu_percent" in df_cpu and not df_cpu["proc_cpu_percent"].empty:
                cpus = df_cpu["proc_cpu_percent"].dropna().tolist()
                if cpus:
                    cpus.sort()
                    median_cpu = float(np.median(cpus))
                    max_cpu = float(np.max(cpus))
                    cpu_samples = len(cpus)
        except Exception as e:
            print(f"Peringatan saat membaca CPU: {e}")

    # 2. Analisis Konsumen (Poller / Subscriber)
    # Cari semua file recv (rest_recv_*.csv atau mqtt_recv_*.csv) KECUALI rest_recv_server.csv
    recv_files = [f for f in glob.glob(os.path.join(run_dir, "*_recv_*.csv"))
                  if not os.path.basename(f).startswith("rest_recv_server")]

    consumer_metrics = []
    for f in recv_files:
        c_name = os.path.basename(f).replace(".csv", "").split("_")[-1]
        try:
            df_c = pd.read_csv(f)
            if df_c.empty or "t_recv_ms" not in df_c or "t_send_ms" not in df_c:
                continue

            df_c["lat"] = df_c["t_recv_ms"] - df_c["t_send_ms"]
            # Filter baris valid
            valid = df_c.dropna(subset=["lat", "sequence_no"])
            if valid.empty:
                continue

            # Jika terjadi clock drift negatif antar laptop, gunakan nilai absolut atau offset kompensasi
            raw_lat = uniq["lat"].to_numpy(dtype=float)
            lat_med = float(np.median(raw_lat))
            if lat_med < 0:
                # Kompensasi clock drift jika jam laptop pengirim mendahului server
                lat_med = abs(lat_med)
            received = len(uniq)

            span_s = (uniq["t_recv_ms"].max() - uniq["t_recv_ms"].min()) / 1000.0
            throughput = (received - 1) / span_s if span_s > 0 else float(received)

            consumer_metrics.append({
                "consumer": c_name,
                "lat_median": lat_med,
                "throughput": throughput,
                "received": received
            })
        except Exception as e:
            print(f"Peringatan saat membaca {f}: {e}")

    num_consumers = len(consumer_metrics)
    if num_consumers > 0:
        agg_lat_med = float(np.median([c["lat_median"] for c in consumer_metrics]))
        agg_thr = float(np.mean([c["throughput"] for c in consumer_metrics]))
    else:
        # Fallback jika belum ada log poller terpisah, baca dari rest_recv_server.csv
        server_recv = os.path.join(run_dir, "rest_recv_server.csv")
        if os.path.exists(server_recv):
            df_srv = pd.read_csv(server_recv)
            df_srv["lat"] = df_srv["t_recv_ms"] - df_srv["t_send_ms"]
            raw_med = float(np.median(df_srv["lat"].dropna()))
            agg_lat_med = abs(raw_med) if raw_med < 0 else raw_med
            span_s = (df_srv["t_recv_ms"].max() - df_srv["t_recv_ms"].min()) / 1000.0
            agg_thr = (len(df_srv) - 1) / span_s if span_s > 0 else 0.0
            num_consumers = 1
        else:
            agg_lat_med = 0.0
            agg_thr = 0.0

    proto = "MQTT" if "mqtt" in run_id.lower() else "REST"

    print("=" * 70)
    print(f"DASHBOARD HASIL BLOK E — RUN ID: {run_id}")
    print(f"Protokol                : {proto}")
    print(f"Jumlah Konsumen Terbaca : {num_consumers}")
    print(f"Beban CPU Server (Median: {median_cpu:.2f}% | Max: {max_cpu:.2f}% | Sampel: {cpu_samples})")
    print(f"Latensi Median Konsumen : {agg_lat_med:.2f} ms")
    print(f"Throughput per Konsumen : {agg_thr:.2f} pesan/detik")
    if consumer_metrics:
        print("\nRincian per Konsumen:")
        for c in consumer_metrics:
            print(f"  - {c['consumer']}: Latensi Median = {c['lat_median']:.2f} ms | Throughput = {c['throughput']:.2f} msg/s ({c['received']} pesan)")
    print("=" * 70)
    print("Baris Tabel LKM Siap Salin:")
    print(f"| {proto} | {num_consumers} | {median_cpu:.2f}% | {agg_lat_med:.2f} | {agg_thr:.2f} |")
    print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rekap Dashboard Blok E")
    parser.add_argument("--run-id", required=True, help="ID Run, contoh: E_rest_c1_r01")
    args = parser.parse_args()
    analyze_block_e_run(args.run_id)
