#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analisis log eksperimen MQTT vs REST.

Konvensi run-id : <kondisi>_r<NN>   contoh: B_rest_N2_r01, C_mqtt_lan_r03
                  -> kondisi = "B_rest_N2", nomor run = 1
Struktur log    : logs/<run-id>/<protocol>_<send|recv>_<nama>.csv

Per run & per konsumen dihitung:
  latensi p50/p95/p99 (t_recv - t_send), throughput (pesan/detik),
  % pesan hilang, duplikat, payload rata-rata, RTT REST (dari log pengirim).
Lalu per kondisi: buang N run pertama (warm-up), laporkan MEDIAN dan IQR antar-run.

Contoh:
  python analysis/analyze.py                      # semua run di logs/
  python analysis/analyze.py --runs "B_*"         # hanya Blok B
  python analysis/analyze.py --warmup 0           # tanpa membuang warm-up
"""

import os
import re
import sys
import glob
import argparse

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_RE = re.compile(r"^(?P<cond>.+?)_r(?P<num>\d+)$")
FILE_RE = re.compile(r"^(?P<proto>mqtt|rest)_(?P<role>send|recv)_(?P<name>.+)\.csv$")


def pct(s, q):
    return float(np.percentile(s, q)) if len(s) else np.nan


def split_run(run_id):
    m = RUN_RE.match(run_id)
    return (m.group("cond"), int(m.group("num"))) if m else (run_id, 0)


def load_run(run_dir):
    send, recv = {}, {}
    for path in glob.glob(os.path.join(run_dir, "*.csv")):
        m = FILE_RE.match(os.path.basename(path))
        if not m:
            continue
        try:
            df = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            continue
        if df.empty:
            continue
        key = (m.group("proto"), m.group("name"))
        (send if m.group("role") == "send" else recv)[key] = df
    return send, recv


def analyze_run(run_id, run_dir):
    cond, num = split_run(run_id)
    send, recv = load_run(run_dir)
    rows = []

    # Jumlah terkirim per (protocol, node) dari log pengirim
    sent = {}
    rtt = {}
    for (proto, _), df in send.items():
        for node, g in df.groupby("node_id"):
            sent[(proto, str(node))] = int(g["sequence_no"].nunique())
        if "rtt_ms" in df:
            r = pd.to_numeric(df["rtt_ms"], errors="coerce").dropna()
            rtt.setdefault(proto, []).extend(r.tolist())

    for (proto, consumer), df in recv.items():
        df = df.copy()
        df["node_id"] = df["node_id"].astype(str)
        df["lat"] = df["t_recv_ms"] - df["t_send_ms"]
        uniq = df.drop_duplicates(["node_id", "sequence_no"])
        lat = uniq["lat"].to_numpy(dtype=float)

        expected = 0
        source = "log pengirim"
        for node, g in uniq.groupby("node_id"):
            if (proto, node) in sent:
                expected += sent[(proto, node)]
            else:  # fallback: rentang sequence_no
                expected += int(g["sequence_no"].max() - g["sequence_no"].min() + 1)
                source = "rentang seq"
        received = len(uniq)
        loss = 100.0 * max(expected - received, 0) / expected if expected else np.nan

        span_s = (uniq["t_recv_ms"].max() - uniq["t_recv_ms"].min()) / 1000.0
        thr = (received - 1) / span_s if span_s > 0 else np.nan

        r = rtt.get(proto, [])
        rows.append({
            "run_id": run_id, "kondisi": cond, "run_no": num,
            "protocol": proto, "consumer": consumer,
            "n_node": uniq["node_id"].nunique(),
            "diterima": received, "diharapkan": expected, "sumber_expected": source,
            "loss_pct": round(loss, 3),
            "duplikat": int(len(df) - received),
            "lat_p50_ms": pct(lat, 50), "lat_p95_ms": pct(lat, 95), "lat_p99_ms": pct(lat, 99),
            "lat_mean_ms": float(np.mean(lat)) if len(lat) else np.nan,
            "lat_std_ms": float(np.std(lat)) if len(lat) else np.nan,
            "lat_negatif": int((lat < 0).sum()),
            "throughput_msg_s": thr,
            "payload_bytes_mean": float(df["payload_bytes"].mean()),
            "rtt_p50_ms": pct(r, 50), "rtt_p95_ms": pct(r, 95),
            "rtt_std_ms": float(np.std(r)) if r else np.nan,
        })
    return rows


def iqr(s):
    s = s.dropna()
    return float(np.percentile(s, 75) - np.percentile(s, 25)) if len(s) else np.nan


def summarize(per_run, warmup):
    kept = []
    for cond, g in per_run.groupby("kondisi"):
        nums = sorted(g["run_no"].unique())
        drop = set(nums[:warmup]) if len(nums) > warmup else set()
        kept.append(g[~g["run_no"].isin(drop)])
    kept = pd.concat(kept) if kept else per_run

    metrics = ["lat_p50_ms", "lat_p95_ms", "lat_p99_ms", "throughput_msg_s",
               "loss_pct", "payload_bytes_mean", "rtt_p50_ms", "rtt_std_ms"]
    out = []
    for (cond, proto), g in kept.groupby(["kondisi", "protocol"]):
        row = {"kondisi": cond, "protocol": proto,
               "n_run": g["run_no"].nunique(), "n_konsumen": g["consumer"].nunique()}
        for m in metrics:
            row[f"{m}_median"] = float(g[m].median()) if g[m].notna().any() else np.nan
            row[f"{m}_iqr"] = iqr(g[m])
        out.append(row)
    return pd.DataFrame(out), kept


def to_markdown(summary):
    cols = [("lat_p50_ms", "p50 (ms)"), ("lat_p95_ms", "p95 (ms)"), ("lat_p99_ms", "p99 (ms)"),
            ("throughput_msg_s", "Throughput (msg/s)"), ("loss_pct", "% hilang"),
            ("payload_bytes_mean", "Payload (B)")]
    head = "| Kondisi | Protokol | Run | " + " | ".join(c[1] for c in cols) + " |"
    sep = "|" + "---|" * (3 + len(cols))
    lines = [head, sep]
    for _, r in summary.sort_values(["kondisi", "protocol"]).iterrows():
        cells = []
        for key, _ in cols:
            med, q = r[f"{key}_median"], r[f"{key}_iqr"]
            cells.append("-" if pd.isna(med) else f"{med:.2f} (IQR {q:.2f})")
        lines.append(f"| {r['kondisi']} | {r['protocol']} | {r['n_run']} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def plot(kept, log_dir, out_dir):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    data, labels = [], []
    for (cond, proto), g in kept.groupby(["kondisi", "protocol"]):
        lats = []
        for run_id in g["run_id"].unique():
            _, recv = load_run(os.path.join(log_dir, run_id))
            for (p, _), df in recv.items():
                if p == proto:
                    lats.extend((df["t_recv_ms"] - df["t_send_ms"]).tolist())
        if lats:
            data.append(lats)
            labels.append(f"{cond}\n{proto}")
    if not data:
        return None
    fig, ax = plt.subplots(figsize=(max(6, 1.4 * len(data)), 5))
    ax.boxplot(data, showfliers=False)
    ax.set_xticks(range(1, len(labels) + 1), labels, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("Latensi (ms)")
    ax.set_title("Distribusi latensi per kondisi (tanpa outlier)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    path = os.path.join(out_dir, "latency_boxplot.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main():
    ap = argparse.ArgumentParser(description="Analisis log MQTT vs REST")
    ap.add_argument("--log-dir", default=os.path.join(ROOT, "logs"))
    ap.add_argument("--runs", default="*", help="Glob nama run (default: semua)")
    ap.add_argument("--warmup", type=int, default=2, help="Jumlah run awal yang dibuang per kondisi")
    ap.add_argument("--out", default=os.path.join(ROOT, "analysis", "out"))
    args = ap.parse_args()

    run_dirs = sorted(d for d in glob.glob(os.path.join(args.log_dir, args.runs))
                      if os.path.isdir(d) and not os.path.basename(d).startswith("_"))
    rows = []
    for d in run_dirs:
        rows.extend(analyze_run(os.path.basename(d), d))
    if not rows:
        print(f"Tidak ada log penerima ditemukan di {args.log_dir} (pola: {args.runs}).")
        sys.exit(1)

    os.makedirs(args.out, exist_ok=True)
    per_run = pd.DataFrame(rows)
    summary, kept = summarize(per_run, args.warmup)

    per_run.to_csv(os.path.join(args.out, "per_run.csv"), index=False)
    summary.to_csv(os.path.join(args.out, "summary.csv"), index=False)
    md = to_markdown(summary)
    with open(os.path.join(args.out, "summary.md"), "w", encoding="utf-8") as f:
        f.write(md + "\n")
    img = plot(kept, args.log_dir, args.out)

    pd.set_option("display.width", 200)
    print("=== Per run ===")
    print(per_run[["run_id", "protocol", "consumer", "diterima", "diharapkan", "loss_pct",
                   "lat_p50_ms", "lat_p95_ms", "lat_p99_ms", "throughput_msg_s",
                   "lat_negatif"]].round(2).to_string(index=False))
    print(f"\n=== Ringkasan (median & IQR, warm-up dibuang: {args.warmup}) ===")
    print(md)
    if per_run["lat_negatif"].sum() > 0:
        print("\n[!] Ada latensi negatif -> jam antar-laptop belum sinkron. Sinkronkan NTP atau pakai RTT.")
    print(f"\nOutput: {args.out}" + (f"\nGrafik: {img}" if img else ""))


if __name__ == "__main__":
    main()
