# Eksperimen Sensor Suhu Terdistribusi: MQTT vs REST

# Anggota Kelompok
- Jildan Adam Zein
- Muhammad Ahsanul Furqon Al Fikri
- Muhammad Rakha Rasyadi
- Adwa` Muhammad Asytar


Repositori praktikum mata kuliah **Sistem Terdistribusi (S2)** untuk eksperimen komparasi protokol komunikasi IoT/M2M:
- **MQTT**: Publish/Subscribe berbasis broker (EMQX Cloud Serverless over TLS).
- **REST**: Request/Response berbasis HTTP POST / GET (Flask server).

Metrik yang diukur: **Latensi (p50, p95, p99)**, **Throughput (pesan/detik)**, **Overhead payload**, dan **Ketahanan Jaringan (% packet loss)**.

---

## 🚀 Panduan Setup Cepat (Wajib untuk 4 Laptop)

Lakukan langkah ini sekali saja di laptop masing-masing setelah melakukan `git clone`:

### 1. Buat Virtual Environment & Install Dependensi
Buka terminal PowerShell di folder repositori ini:
```powershell
# Buat virtual environment
py -m venv .venv

# Install dependensi (versi terkunci agar seragam di semua laptop)
.\.venv\Scripts\pip install -r requirements-lock.txt
```

### 2. Konfigurasi Kredensial Broker MQTT (`.env`)
Salin file template `.env.example` menjadi `.env`:
```powershell
Copy-Item MQTT\.env.example MQTT\.env
```
Buka file `MQTT/.env` dengan teks editor (Notepad / VS Code), lalu isi nilainya:
```env
MQTT_BROKER=j9196c62.ala.asia-southeast1.emqxsl.com
MQTT_PORT=8883
MQTT_TLS=1
MQTT_USERNAME=sister
MQTT_PASSWORD=sister123
MQTT_TOPIC=sister/temp
```
> ⚠️ **PENTING:** Berkas `.env` berisi password dan **otomatis diabaikan oleh Git** (`.gitignore`). Jangan pernah mengunggah kredensial ke Git.

### 3. Uji Coba Koneksi Broker
Jalankan skrip tes berikut:
```powershell
.\.venv\Scripts\python MQTT\check_mqtt.py
```
*Pastikan output di terminal menampilkan:* `>>> HASIL: SUKSES <<<`.

---

## 👥 Pembagian Peran Laptop (JOBDESK)

| Laptop | Peran Utama | Tugas & Tanggung Jawab |
| :---: | :--- | :--- |
| **L1** | **Server & Logger Pusat** | Menjalankan REST Server & MQTT Subscriber; Mengumpulkan seluruh file log CSV dari L2–L4. |
| **L2** | **Pengirim Utama** | Pengirim aktif di semua blok (Blok A s.d. F); Menjadi poller-1 di Blok E. |
| **L3** | **Pengirim / Konsumen-2** | Masuk saat kondisi N=3 dan N=4; Menjadi konsumen/poller-2 di Blok E. |
| **L4** | **Pengirim / Korban Fault** | Masuk saat N=4; Operator pemutusan Wi-Fi 15 detik pada Blok D; Konsumen-3 di Blok E. |

---

## 📋 Panduan Eksekusi Per Blok Eksperimen

Gunakan IP Wi-Fi milik Laptop 1 untuk menggantikan `<IP-L1>` (misalnya `http://192.168.1.50:5151`).

### Blok A — Validasi Fungsional (1 Laptop)
Tujuan: Memastikan alur data masuk dan log CSV tercatat lengkap.
```powershell
# Terminal 1 (REST Server):
.\.venv\Scripts\python REST\server.py --log logs/A_rest.csv

# Terminal 2 (MQTT Subscriber):
.\.venv\Scripts\python MQTT\sub.py --log logs/A_mqtt.csv

# Terminal 3 (REST Client):
.\.venv\Scripts\python REST\client.py --server http://127.0.0.1:5151 --node-id laptop2 --count 20 --log logs/A_laptop2_rest.csv

# Terminal 4 (MQTT Publisher):
.\.venv\Scripts\python MQTT\pub.py --node-id laptop2 --count 20 --log logs/A_laptop2_mqtt.csv
```

---

### Blok B — Skalabilitas Node (2, 3, 4 Laptop; Wi-Fi Kampus; 1 Konsumen)
*Lakukan 10 run per kondisi (`r01` s.d. `r10`), masing-masing run mengirim 60–100 pesan.*

- **Laptop 1 (Penerima):**
  ```powershell
  # REST:
  .\.venv\Scripts\python REST\server.py --log logs/B_rest_N2_r01.csv
  # MQTT:
  .\.venv\Scripts\python MQTT\sub.py --log logs/B_mqtt_N2_r01.csv
  ```
- **Laptop Pengirim (L2, L3, L4):**
  - **Kondisi N=2**: Hanya **L2** yang mengirim (`--node-id laptop2`).
  - **Kondisi N=3**: **L2** dan **L3** mengirim serentak (`--node-id laptop2` dan `--node-id laptop3`).
  - **Kondisi N=4**: **L2**, **L3**, dan **L4** mengirim serentak.
  ```powershell
  # Contoh perintah di Laptop 3 (REST):
  .\.venv\Scripts\python REST\client.py --server http://<IP-L1>:5151 --node-id laptop3 --count 60 --log logs/B_laptop3_N3_r01.csv

  # Contoh perintah di Laptop 3 (MQTT):
  .\.venv\Scripts\python MQTT\pub.py --node-id laptop3 --count 60 --log logs/B_laptop3_N3_mqtt_r01.csv
  ```

---

### Blok C — Kualitas Jaringan & Overhead (4 Laptop)
Uji 3 kondisi jaringan: **LAN kabel**, **Wi-Fi kampus**, dan **Wi-Fi dibatasi/Hotspot**.
- Tangkap paket dengan **Wireshark** untuk mengukur overhead:
  - Filter REST: `http or tcp.port == 5151`
  - Filter MQTT: `mqtt or tcp.port == 8883`
- Untuk jalur REST lintas jaringan (Wi-Fi dibatasi / internet):
  Laptop 1 menjalankan **ngrok**: `ngrok http 5151`, lalu pengirim mengarahkan `--server https://<id-ngrok>.ngrok-free.app`.

---

### Blok D — Ketahanan Jaringan / Fault Injection (4 Laptop)
Uji pemutusan adapter Wi-Fi pada laptop pengirim utama (**L4**) selama 15 detik:

1. **Laptop 1 (Penerima):** Jalankan `server.py` dan `sub.py --persistent`.
2. **Laptop 4 (Korban):** Buka 2 terminal:
   ```powershell
   # Terminal 1: Pengirim MQTT (dengan sesi persisten & QoS 1)
   .\.venv\Scripts\python MQTT\pub.py --node-id laptop4 --qos 1 --persistent --log logs/D_laptop4_mqtt_r01.csv

   # Terminal 2: Pencatat Waktu Putus / Pulih
   .\.venv\Scripts\python tools\fault_marker.py --protocol mqtt --run-id D_r01
   ```
   *Instruksi:* Tekan `ENTER` tepat saat mematikan Wi-Fi, lalu tekan `ENTER` lagi saat menyalakan kembali Wi-Fi. **Jangan matikan proses Python!**

---

### Blok E — Fan-Out Konsumen (3 Node Pengirim Tetap)
Mengukur beban CPU server/broker saat konsumen (dashboard) ditambah: 1 -> 2 -> 3 konsumen.

- **Jalur REST (Pull / Polling):**
  1. Laptop 1 menjalankan server & monitor CPU:
     ```powershell
     .\.venv\Scripts\python REST\server.py --run-id E_rest_c1_r01
     .\.venv\Scripts\python tools\cpu_monitor.py --match server.py --run-id E_rest_c1_r01
     ```
  2. Pengirim tetap (L2, L3, L4) mengirim data suhu.
  3. Jalankan konsumen polling bertahap (1, 2, atau 3 terminal):
     ```powershell
     .\.venv\Scripts\python REST\poller.py --server http://<IP-L1>:5151 --consumer-id poll1 --run-id E_rest_c1_r01
     ```
- **Jalur MQTT (Push):**
  Tambahkan subscriber bertahap:
  ```powershell
  .\.venv\Scripts\python MQTT\sub.py --consumer-id sub1 --run-id E_mqtt_c1_r01
  .\.venv\Scripts\python MQTT\sub.py --consumer-id sub2 --run-id E_mqtt_c1_r01
  ```

---

### Blok F — QoS MQTT (Opsional, QoS 0, 1, 2)
Jalankan publisher dengan variasi `--qos`:
```powershell
.\.venv\Scripts\python MQTT\pub.py --qos 0 --count 50 --log logs/F_pub_qos0.csv
.\.venv\Scripts\python MQTT\pub.py --qos 1 --count 50 --log logs/F_pub_qos1.csv
.\.venv\Scripts\python MQTT\pub.py --qos 2 --count 50 --log logs/F_pub_qos2.csv
```

---

## 📊 Analisis Data Otomatis & Visualisasi

Setelah eksperimen selesai, kumpulkan file log CSV dari semua laptop ke folder `logs/` di Laptop 1, lalu jalankan:

```powershell
# Analisis seluruh data (otomatis buang 2 run warm-up):
.\.venv\Scripts\python analysis\analyze.py

# Analisis blok tertentu:
.\.venv\Scripts\python analysis\analyze.py --runs "B_*"
```

**Hasil yang digenerate di `analysis/out/`:**
1. `summary.md` : Tabel Markdown ringkasan nilai **p50, p95, p99 (ms)**, throughput, packet loss, dan payload rata-rata (langsung salin ke laporan LKM).
2. `latency_boxplot.png` : Gambar boxplot distribusi latensi untuk disematkan di dokumen laporan.
3. `per_run.csv` : Detail lengkap per run eksperimen.

---

## 📁 Struktur Repositori

```text
├── MQTT/
│   ├── check_mqtt.py         # Skrip uji koneksi broker EMQX
│   ├── pub.py                # Publisher pengirim data suhu
│   ├── sub.py                # Subscriber penerima data suhu
│   └── .env.example          # Template konfigurasi kredensial broker
├── REST/
│   ├── client.py             # Client pengirim data suhu (HTTP POST)
│   ├── server.py             # Server penerima data (Flask)
│   └── poller.py             # Konsumen polling dashboard (HTTP GET)
├── common/
│   ├── config.py             # Handler .env dan konfigurasi broker
│   └── csvlog.py             # Logger thread-safe skema 8 kolom LKM
├── tools/
│   ├── cpu_monitor.py        # Pemantau utilisasi CPU server/broker (Blok E)
│   └── fault_marker.py       # Pencatat timestamp putus/pulih jaringan (Blok D)
├── analysis/
│   └── analyze.py            # Kalkulator p50/p95/p99, throughput, loss & boxplot
├── requirements.txt          # Daftar pustaka & dependensi
├── requirements-lock.txt     # Pin versi dependensi yang seragam
├── JOBDESK.md                # Rincian detail tugas per laptop (L1 - L4)
└── README.md                 # Dokumentasi & panduan eksekusi ini
```
