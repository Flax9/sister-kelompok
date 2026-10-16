# Panduan Pelaksanaan Eksperimen LKM Sensor Suhu: MQTT vs REST

Repositori ini telah disiapkan dan diuji untuk seluruh blok eksperimen pada LKM Sistem Terdistribusi.

---

## 1. Setup Environment (Untuk Setiap Laptop Kelompok)

Jalankan perintah berikut di PowerShell dari folder `Sister`:

```powershell
# 1. Buat virtual environment
py -m venv .venv

# 2. Pasang pustaka sesuai requirements
.\.venv\Scripts\pip install -r requirements-lock.txt
```

### Mengisi Kredensial Broker (EMQX / HiveMQ)
Salin berkas `MQTT/.env.example` menjadi `MQTT/.env`:
```powershell
Copy-Item MQTT\.env.example MQTT\.env
```
Buka `MQTT/.env` lalu isi kredensial yang diberikan rekan Anda:
```env
MQTT_BROKER=xxxxxx.ala.asia-southeast1.emqxsl.com
MQTT_PORT=8883
MQTT_TLS=true
MQTT_USERNAME=user_kelompok
MQTT_PASSWORD=password_kelompok
MQTT_CA_CERT=             # Kosongkan jika memakai sertifikat publik, atau isi path .crt jika ada
MQTT_TOPIC=sister/kelompok_anda/temp
```
*(Jika `.env` belum diisi, skrip otomatis memakai broker publik `broker.hivemq.com:1883` tanpa TLS untuk uji coba).*

---

## 2. Struktur Berkas Praktikum

| Folder / Berkas | Fungsi |
| :--- | :--- |
| [requirements.txt](file:///d:/Backup/S2/Sister/requirements.txt) | Daftar seluruh library yang dibutuhkan & catatannya |
| [requirements-lock.txt](file:///d:/Backup/S2/Sister/requirements-lock.txt) | Pin versi persis untuk reproduksibilitas antar-laptop |
| [common/config.py](file:///d:/Backup/S2/Sister/common/config.py) | Handler `.env` & koneksi broker MQTT |
| [common/csvlog.py](file:///d:/Backup/S2/Sister/common/csvlog.py) | Logger CSV thread-safe sesuai 8 skema inti LKM |
| [MQTT/pub.py](file:///d:/Backup/S2/Sister/MQTT/pub.py) | Publisher node pengirim sensor (MQTT) |
| [MQTT/sub.py](file:///d:/Backup/S2/Sister/MQTT/sub.py) | Subscriber konsumen penerima data (MQTT) |
| [REST/client.py](file:///d:/Backup/S2/Sister/REST/client.py) | Client node pengirim sensor (REST HTTP POST) |
| [REST/server.py](file:///d:/Backup/S2/Sister/REST/server.py) | Server penerima data & penyedia endpoint polling |
| [REST/poller.py](file:///d:/Backup/S2/Sister/REST/poller.py) | Konsumen polling dashboard (REST HTTP GET) |
| [tools/cpu_monitor.py](file:///d:/Backup/S2/Sister/tools/cpu_monitor.py) | Pengukur beban CPU server/broker (Blok E) |
| [tools/fault_marker.py](file:///d:/Backup/S2/Sister/tools/fault_marker.py) | Penanda event pemutusan Wi-Fi (Blok D) |
| [analysis/analyze.py](file:///d:/Backup/S2/Sister/analysis/analyze.py) | Skrip kalkulasi otomatis (p50/p95/p99, throughput, packet loss, grafik) |

---

## 3. Cara Menjalankan Tiap Blok Eksperimen

Gunakan parameter `--run-id <KONDISI>_r<NOMOR>` yang **sama** pada pengirim dan penerima di setiap run. Contoh: `B_rest_N2_r01`.

### Blok A — Validasi Fungsional (1 Laptop)
Uji coba bahwa data sampai dan tercatat di CSV:
```powershell
# Terminal 1 (REST Server):
.\.venv\Scripts\python REST\server.py --run-id A_smoke_r01

# Terminal 2 (REST Client):
.\.venv\Scripts\python REST\client.py --run-id A_smoke_r01 --count 20

# Terminal 3 (MQTT Subscriber):
.\.venv\Scripts\python MQTT\sub.py --run-id A_smoke_r01

# Terminal 4 (MQTT Publisher):
.\.venv\Scripts\python MQTT\pub.py --run-id A_smoke_r01 --count 20
```

---

### Blok B — Skalabilitas Node (2, 3, 4 Laptop; Wi-Fi Kampus; 1 Konsumen)
*Lakukan 10 kali run per kondisi (r01 s.d. r10).*

**Jalur REST:**
- **Laptop 1 (Server):**
  ```powershell
  .\.venv\Scripts\python REST\server.py --run-id B_rest_N2_r01
  ```
- **Laptop 2..N (Node Pengirim Sensor):**
  ```powershell
  .\.venv\Scripts\python REST\client.py --server http://<IP_LAPTOP_1>:5151/sensor --node-id laptop2 --count 60 --run-id B_rest_N2_r01
  ```

**Jalur MQTT:**
- **Laptop 1 (Subscriber):**
  ```powershell
  .\.venv\Scripts\python MQTT\sub.py --run-id B_mqtt_N2_r01
  ```
- **Laptop 2..N (Publisher):**
  ```powershell
  .\.venv\Scripts\python MQTT\pub.py --node-id laptop2 --count 60 --run-id B_mqtt_N2_r01
  ```

---

### Blok C — Kualitas Jaringan & Overhead (4 Laptop)
Uji pada 3 kondisi: LAN kabel, Wi-Fi kampus, Wi-Fi dibatasi (hotspot HP).
- Jalankan Wireshark pada antarmuka jaringan yang aktif:
  - Filter Wireshark REST: `http or tcp.port == 5151`
  - Filter Wireshark MQTT: `mqtt or tcp.port == 8883`
- Untuk jalur REST lintas jaringan (Wi-Fi dibatasi/internet):
  Gunakan **ngrok** di laptop server:
  ```powershell
  ngrok http 5151
  ```
  Lalu di laptop client arahkan `--server https://<id-ngrok>.ngrok-free.app/sensor`.
- Jalankan pengiriman dengan format run ID: `C_rest_lan_r01`, `C_mqtt_lan_r01`, `C_rest_wifi_r01`, dst.

---

### Blok D — Ketahanan / Fault Injection (4 Laptop)
Uji ketahanan saat adapter Wi-Fi laptop pengirim dimatikan 15 detik di tengah jalan:

- **Laptop Konsumen:** jalankan `sub.py` (untuk MQTT gunakan flag `--persistent` dan QoS 1) atau `server.py`.
- **Laptop Pengirim:**
  Buka 2 terminal berdampingan:
  ```powershell
  # Terminal 1: Pengirim (kirim terus menerus dengan interval 1 detik)
  .\.venv\Scripts\python MQTT\pub.py --qos 1 --persistent --run-id D_mqtt_r01

  # Terminal 2: Penanda waktu putus/pulih
  .\.venv\Scripts\python tools\fault_marker.py --protocol mqtt --run-id D_mqtt_r01
  ```
  *Instruksi:* Tekan ENTER pada Terminal 2 tepat saat mematikan Wi-Fi, lalu tekan ENTER lagi saat menyalakan kembali Wi-Fi.

---

### Blok E — Fan-out Konsumen (3 Node Pengirim Tetap)
Menguji beban server/broker saat konsumen (dashboard) ditambah: 1 -> 2 -> 3 konsumen.

- **Jalur REST (Polling):**
  1. Jalankan `REST\server.py --run-id E_rest_c1_r01`.
  2. Jalankan `tools\cpu_monitor.py --match server.py --run-id E_rest_c1_r01`.
  3. Jalankan 3 client pengirim suhu.
  4. Jalankan 1, 2, atau 3 poller di terminal/laptop terpisah:
     ```powershell
     .\.venv\Scripts\python REST\poller.py --server http://<IP_SERVER>:5151 --consumer-id poll1 --run-id E_rest_c1_r01
     ```

- **Jalur MQTT (Push):**
  1. Jalankan 3 publisher pengirim suhu.
  2. Jalankan 1, 2, atau 3 subscriber dengan ID konsumen berbeda:
     ```powershell
     .\.venv\Scripts\python MQTT\sub.py --consumer-id sub1 --run-id E_mqtt_c1_r01
     .\.venv\Scripts\python MQTT\sub.py --consumer-id sub2 --run-id E_mqtt_c1_r01
     ```

---

### Blok F — QoS MQTT (Opsional, QoS 0, 1, 2)
Jalankan pengujian dengan variasi parameter `--qos`:
```powershell
.\.venv\Scripts\python MQTT\pub.py --qos 0 --run-id F_qos0_r01 --count 50
.\.venv\Scripts\python MQTT\pub.py --qos 1 --run-id F_qos1_r01 --count 50
.\.venv\Scripts\python MQTT\pub.py --qos 2 --run-id F_qos2_r01 --count 50
```

---

## 4. Analisis Data & Visualisasi Otomatis

Kumpulkan seluruh folder log dari laptop anggota ke dalam satu folder `logs/`, lalu jalankan:

```powershell
# Analisis seluruh data (otomatis buang 2 run warm-up, hitung p50/p95/p99 & IQR):
.\.venv\Scripts\python analysis\analyze.py

# Analisis blok tertentu saja (misal hanya Blok B):
.\.venv\Scripts\python analysis\analyze.py --runs "B_*"
```

**Hasil yang dihasilkan di folder `analysis/out/`:**
1. `summary.md` : Tabel Markdown ringkasan per kondisi (siap salin langsung ke laporan).
2. `per_run.csv` : Metrik detail per run (p50, p95, p99, throughput, packet loss, bytes).
3. `latency_boxplot.png` : Gambar boxplot distribusi latensi untuk disematkan di laporan praktikum.
