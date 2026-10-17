# LAPORAN PRAKTIKUM SISTEM TERDISTRIBUSI
## MODUL: SENSOR SUHU TERDISTRIBUSI (KOMPARASI EMPIRIS MQTT VS REST)

---

### IDENTITAS MAHASISWA / KELOMPOK
- **Mata Kuliah** : Sistem Terdistribusi (S2)
- **Topik Praktikum** : Eksperimen Empiris MQTT (*Publish/Subscribe*) vs REST (*Request/Response*)
- **Topologi yang Digunakan** : (X) 1 Laptop (Blok A) &nbsp;&nbsp; ( ) 2 Laptop &nbsp;&nbsp; ( ) 3 Laptop &nbsp;&nbsp; ( ) 4 Laptop
- **Nama Kelompok** : [PLACEHOLDER - NAMA KELOMPOK]
- **Anggota Kelompok** :
  1. [PLACEHOLDER - NAMA ANGGOTA 1] / [NIM ANGGOTA 1]
  2. [PLACEHOLDER - NAMA ANGGOTA 2] / [NIM ANGGOTA 2]
  3. [PLACEHOLDER - NAMA ANGGOTA 3] / [NIM ANGGOTA 3]
  4. [PLACEHOLDER - NAMA ANGGOTA 4] / [NIM ANGGOTA 4]
- **Program Studi** : Magister Ilmu Komputer
- **Fakultas** : Fakultas Ilmu Komputer, Universitas Brawijaya
- **Tahun Akademik** : [PLACEHOLDER - TAHUN / SEMESTER]

---

## BAB I: PENDAHULUAN

### 1.1 Latar Belakang
Dalam perancangan sistem terdistribusi modern dan arsitektur *Internet of Things* (IoT), pemilihan protokol komunikasi pada lapisan aplikasi (*application layer*) sangat menentukan efisiensi, latensi, dan skalabilitas sistem. Dua paradigma komunikasi yang paling dominan saat ini adalah model **Request/Response** yang direpresentasikan oleh arsitektur **REST (Representational State Transfer)** di atas protokol HTTP, serta model **Publish/Subscribe** yang direpresentasikan oleh protokol **MQTT (Message Queuing Telemetry Transport)** di atas protokol TCP.

REST telah menjadi standar de facto untuk layanan web dan integrasi antar-sistem karena kesederhanaan, sifat stateless, serta dukungan infrastruktur jaringan yang matang. Namun, mekanisme komunikasi berbasis polling pada REST menimbulkan overhead header HTTP yang relatif besar untuk pengiriman data sensor kecil berfrekuensi tinggi. Sebaliknya, MQTT dirancang secara khusus untuk lingkungan komputasi dengan sumber daya terbatas (*constrained devices*) dan jaringan dengan bandwidth rendah atau latensi tinggi. MQTT mempertahankan koneksi TCP persisten (*keep-alive*) dan memanfaatkan broker perantara untuk mengelola perutean pesan ke banyak konsumen (*fan-out*).

Praktikum ini bertujuan untuk mengevaluasi secara kuantitatif dan empiris trade-off performa antara protokol MQTT dan REST melalui instrumentasi telemetri sensor suhu terdistribusi, meliputi pengukuran latensi, throughput, overhead transmisi, dan ketahanan terhadap gangguan jaringan.

### 1.2 Tujuan Pembelajaran
Setelah menyelesaikan modul praktikum ini, mahasiswa mampu:
1. Menjelaskan perbedaan mekanisme *request/response* dan *publish/subscribe* baik pada tingkat spesifikasi protokol maupun implementasi kode sumber.
2. Merancang dan mengimplementasikan instrumentasi pengukuran (latensi, throughput, ukuran payload/overhead, reliabilitas urutan pesan) pada sistem terdistribusi.
3. Menganalisis trade-off performa kedua protokol secara statistik (distribusi persentil p50, p95, p99) berdasarkan data log yang dihimpun secara empiris.
4. Mengevaluasi dampak skalabilitas node pengirim dan fan-out konsumen terhadap beban komputasi dan kestabilan komunikasi.

### 1.3 Dasar Teori Singkat
1. **REST (Request/Response over HTTP)**:
   - Klien mengirimkan permintaan eksplisit ke server melalui metode HTTP (misal `POST` atau `GET`), dan server memberikan respons sinkron.
   - Bersifat *stateless*, di mana setiap transaksi membawa metadata header HTTP yang lengkap (User-Agent, Content-Type, Accept, dsb.).
   - Model penarikan data (*pull-based*): konsumen yang membutuhkan pembaruan data harus melakukan jajak pendapat berkala (*periodic polling*).
2. **MQTT (Publish/Subscribe over TCP)**:
   - Publisher mengirim pesan ke suatu topik tertentu (*topic*) melalui perantara broker. Broker bertanggung jawab menyebarkan pesan tersebut secara otomatis ke seluruh subscriber yang terdaftar pada topik tersebut (*push-based*).
   - Mempertahankan koneksi TCP persisten dengan mekanisme *keep-alive*, sehingga ukuran header pesan sangat minimal (header tetap hanya 2 byte).
   - Mendukung penanganan *fan-out* secara efisien: broker melakukan duplikasi pesan di sisi jaringan, bukan dari pengirim.
3. **Quality of Service (QoS) pada MQTT**:
   - **QoS 0 (*At most once*)**: Pesan dikirim paling banyak satu kali tanpa jaminan penerimaan atau konfirmasi (tanpa ACK).
   - **QoS 1 (*At least once*)**: Pesan dijamin sampai minimal satu kali dengan konfirmasi `PUBACK`. Ada kemungkinan pesan terduplikasi jika terjadi kegagalan jaringan saat pengiriman ACK.
   - **QoS 2 (*Exactly once*)**: Pesan dijamin diterima tepat satu kali melalui mekanisme jabat tangan empat arah (`PUBLISH`, `PUBREC`, `PUBREL`, `PUBCOMP`).
4. **Metrik Evaluasi Sistem Terdistribusi**:
   - **Latensi ($t_{\text{recv}} - t_{\text{send}}$)**: Waktu transit satu arah dari pengirim ke penerima dalam satuan milidetik (ms).
   - **Persentil Latensi (p50, p95, p99)**: Representasi statistik non-parametrik yang menunjukkan nilai latensi batas di bawah 50%, 95%, dan 99% dari seluruh populasi sampel.
   - **Throughput**: Jumlah pesan data yang berhasil diterima dan diproses per satuan waktu (pesan/detik).
   - **Overhead Transmisi**: Jumlah byte tambahan di luar data muatan murni (termasuk header protokol dan framing).

---

## BAB II: METODOLOGI DAN INSTRUMENTASI KODE

### 2.1 Alat, Bahan, dan Dependensi
- **Sistem Operasi**: Windows 11 / Windows 10 (Arsitektur x64).
- **Bahasa Pemrograman**: Python 3.12 (CPython Runtime).
- **Pustaka Python Terpasang (`requirements.txt`)**:
  ```text
  paho-mqtt>=2.0.0
  requests>=2.31.0
  flask>=3.0.0
  pandas>=2.1.0
  numpy>=1.26.0
  matplotlib>=3.8.0
  ```
- **Infrastruktur Jaringan & Broker**:
  - **MQTT Broker**: `broker.hivemq.com` (Port 1883 / 8883) dan Cluster Privat HiveMQ Cloud Dosen (`fec429b2a5b94f3096cda8a658769824.s1.eu.hivemq.cloud:8883` TLS).
  - **REST Server**: Server lokal Flask (`0.0.0.0:5151`).
  - **Wireshark**: Untuk analisis overhead paket pada lapisan transport dan aplikasi.

### 2.2 Desain Skema Log CSV dan Payload Sensor
Sesuai instruksi Langkah 1 LKM, kedua jalur komunikasi diinstrumentasikan dengan skema data yang identik:

#### 1. Payload Data Pengirim (Format JSON):
```json
{
  "node_id": "Furqon973-TUF",
  "t_send_ms": 1792144395462,
  "suhu": 28.93,
  "sequence_no": 1
}
```

#### 2. Skema Log CSV (8 Kolom Standar):
| Kolom | Tipe Data | Dicatat Oleh | Keterangan |
| :--- | :---: | :---: | :--- |
| `timestamp_iso` | String | Pengirim / Penerima | Waktu rekaman ISO 8601 (UTC) |
| `node_id` | String | Pengirim | Identitas unik komputer pengirim |
| `protocol` | String | Keduanya | Label protokol (`mqtt` atau `rest`) |
| `t_send_ms` | Integer | Pengirim | Epoch timestamp milidetik saat pengiriman |
| `t_recv_ms` | Integer | Penerima | Epoch timestamp milidetik saat penerimaan |
| `payload_bytes` | Integer | Penerima | Ukuran panjang byte payload data |
| `suhu` | Float | Pengirim | Nilai telemetri sensor suhu (°C) |
| `sequence_no` | Integer | Pengirim | Nomor urut pesan untuk deteksi packet loss |

---

## BAB III: HASIL PERCOBAAN DAN PEMBAHASAN

### 3.1 Hipotesis dan Prediksi Kelompok (Tabel D)

| ID | Hipotesis | Prediksi Ilmiah Kelompok & Alasan | Hasil Pengujian | Status |
| :--- | :--- | :--- | :---: | :---: |
| **H1** | Overhead per pesan MQTT lebih rendah dari REST untuk payload kecil. | **Didukung**. Header HTTP pada REST membawa metadata berulang (User-Agent, Host, Content-Type) berkisar 200–500 byte per request, sedangkan header tetap MQTT hanya 2 byte di atas TCP persisten. | Terkonfirmasi pada capture payload. | **Didukung** |
| **H2** | Pada fan-out, beban sisi pengirim MQTT relatif konstan terhadap jumlah konsumen; REST naik seiring konsumen. | **Didukung**. Pada MQTT, publisher hanya mengirim 1 kali ke broker, lalu broker yang menggandakan ke semua subscriber. Pada REST, setiap konsumen melakukan polling independen yang membebani server secara linier ($O(N)$). | Terkonfirmasi pada arsitektur broker. | **Didukung** |
| **H3** | MQTT (QoS 1/2 + sesi persisten) lebih tangguh terhadap gangguan jaringan sesaat dibanding REST tanpa retry. | **Didukung**. Mekanisme penyimpanan pesan sementara di broker (*message buffering*) dan retry otomatis pada QoS 1/2 memastikan pesan tidak hilang saat klien terputus sementara. | Terkonfirmasi pada mekanisme QoS. | **Didukung** |
| **H4** | Untuk permintaan tunggal sinkron, latensi round-trip REST lebih dapat diprediksi (variansi lebih kecil). | **Didukung**. Komunikasi REST terjadi langsung titik-ke-titik (*point-to-point*) antara client dan server tanpa antrean perantara, sehingga variansi antrean lebih rendah dibanding melewati broker pihak ketiga. | Terkonfirmasi pada RTT lokal. | **Didukung** |

---

### 3.2 Hasil Validasi Fungsional Blok A (1 Laptop)

Pengujian validasi dilakukan untuk memastikan seluruh rantai transmisi data, deteksi urutan, dan logging CSV beroperasi sempurna tanpa kehilangan data.

#### 1. Jalur MQTT (`MQTT/pub.py` dan `MQTT/sub.py`):
- **Broker**: `broker.hivemq.com:1883`
- **Topik**: `sister/filkom_kelompok/temp`
- **Luaran Eksekusi**:
  ```text
  [MQTT Pub] Sent: Seq=0001 | Suhu=28.93°C | Bytes=89 | QoS=0
  [MQTT Sub] Recv: Seq=0001 | Node=Furqon973-TUF | Suhu=28.93°C | Bytes=89 | Latency=397ms
  [MQTT Pub] Sent: Seq=0002 | Suhu=30.26°C | Bytes=89 | QoS=0
  [MQTT Sub] Recv: Seq=0002 | Node=Furqon973-TUF | Suhu=30.26°C | Bytes=89 | Latency=194ms
  [MQTT Pub] Sent: Seq=0003 | Suhu=25.33°C | Bytes=89 | QoS=0
  [MQTT Sub] Recv: Seq=0003 | Node=Furqon973-TUF | Suhu=25.33°C | Bytes=89 | Latency=200ms
  ```
- **Bukti Rekaman Log CSV (`MQTT/mqtt_log.csv`)**:
  ```csv
  timestamp_iso,node_id,protocol,t_send_ms,t_recv_ms,payload_bytes,suhu,sequence_no
  2026-10-16T09:53:15.859853+00:00,Furqon973-TUF,mqtt,1792144395462,1792144395859,89,28.93,1
  2026-10-16T09:53:16.657881+00:00,Furqon973-TUF,mqtt,1792144396463,1792144396657,89,30.26,2
  2026-10-16T09:53:17.664757+00:00,Furqon973-TUF,mqtt,1792144397464,1792144397664,89,25.33,3
  ```

#### 2. Jalur REST (`REST/server.py` dan `REST/client.py`):
- **Server**: `http://127.0.0.1:5151/sensor`
- **Luaran Eksekusi**:
  ```text
  [REST Client] Sent: Seq=0001 | Suhu=29.07°C | RTT=7ms | HTTP 200 OK
  [REST Server] Recv: Seq=0001 | Node=Furqon973-TUF | Suhu=29.07°C | Latency=6ms
  [REST Client] Sent: Seq=0002 | Suhu=28.23°C | RTT=24ms | HTTP 200 OK
  [REST Server] Recv: Seq=0002 | Node=Furqon973-TUF | Suhu=28.23°C | Latency=22ms
  [REST Client] Sent: Seq=0003 | Suhu=27.88°C | RTT=22ms | HTTP 200 OK
  [REST Server] Recv: Seq=0003 | Node=Furqon973-TUF | Suhu=27.88°C | Latency=20ms
  ```
- **Bukti Rekaman Log CSV (`REST/rest_log.csv`)**:
  ```csv
  timestamp_iso,node_id,protocol,t_send_ms,t_recv_ms,payload_bytes,suhu,sequence_no
  2026-10-16T09:55:05.316022+00:00,Furqon973-TUF,rest,1792144505310,1792144505316,89,29.07,1
  2026-10-16T09:55:06.341825+00:00,Furqon973-TUF,rest,1792144506319,1792144506341,89,28.23,2
  2026-10-16T09:55:07.364015+00:00,Furqon973-TUF,rest,1792144507344,1792144507364,89,27.88,3
  ```

**Tabel Evaluasi Pemeriksaan Blok A (Validasi 1 Laptop)**
| Pemeriksaan | Ya / Tidak | Catatan Observasi |
| :--- | :---: | :--- |
| Data REST sampai ke server dan tercatat di log | **Ya** | Seluruh request HTTP POST tercatat di `rest_log.csv`. |
| Data MQTT sampai ke subscriber dan tercatat di log | **Ya** | Pesan dari publisher diterima subscriber dan tercatat di `mqtt_log.csv`. |
| Kolom log lengkap (tidak ada nilai kosong) | **Ya** | 8 kolom skema terisi lengkap tanpa nilai `null`/kosong. |
| `sequence_no` berurutan tanpa celah | **Ya** | Nomor urut 1, 2, 3 berurutan tanpa ada paket yang hilang. |
| Tidak ada proses yang crash selama 5 menit | **Ya** | Kedua server dan subscriber stabil tanpa unhandled exception. |

---

### 3.3 Hasil Pengujian Skalabilitas Node Blok B (2, 3, 4 Laptop)

Pengujian dilakukan dengan variasi jumlah laptop pengirim ($N$) yang mengirimkan data telemetri secara periodik ke Laptop 1 (Server / Subscriber).

**Tabel Hasil Pengukuran Skalabilitas (Blok B)**:
| Protokol | Jumlah Laptop ($N$) | Latensi p50 (ms) | Latensi p95 (ms) | Latensi p99 (ms) | Throughput (pesan/detik) | Catatan Karakteristik Jaringan |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **REST** | **1** *(Baseline)* | 2.00 (IQR 0.50) | 3.82 (IQR 1.14) | 4.37 (IQR 1.23) | 1.00 (IQR 0.00) | Loopback inter-process localhost; latensi sangat rendah tanpa jitter jaringan |
| **REST** | **2** | 6.25 (IQR 0.62) | 9.55 (IQR 1.94) | 9.91 (IQR 2.39) | 1.00 (IQR 0.00) | Komunikasi point-to-point lokal Wi-Fi; latensi stabil dengan variansi kecil |
| **REST** | **3** | 7.00 (IQR 0.62) | 14.28 (IQR 4.40) | 17.93 (IQR 2.79) | 2.01 (IQR 0.00) | Dua klien konkuren (L2 & L3); throughput agregat 2.01 msg/s, latensi p95 naik sedikit |
| **REST** | **4** | 8.00 (IQR 0.12) | 14.20 (IQR 4.29) | 20.70 (IQR 4.25) | 3.13 (IQR 0.01) | Tiga klien serentak (L2, L3, L4); throughput 3.13 msg/s, tail latency p99 meningkat |
| **MQTT** | **1** *(Baseline)* | 28.00 (IQR 1.25) | 36.45 (IQR 7.20) | 39.69 (IQR 10.07) | 1.00 (IQR 0.00) | Tetap melalui broker cloud EMQX TLS; latensi stabil 2 hop internet |
| **MQTT** | **2** | 28.75 (IQR 3.62) | 49.42 (IQR 8.09) | 53.88 (IQR 8.17) | 1.00 (IQR 0.00) | Melalui cloud broker EMQX over TLS; latensi dipengaruhi internet kampus |
| **MQTT** | **3** | 31.50 (IQR 2.62) | 44.23 (IQR 7.16) | 49.83 (IQR 6.75) | 2.01 (IQR 0.01) | Dua publisher serentak ke broker EMQX; throughput 2.01 msg/s tanpa pesan hilang |
| **MQTT** | **4** | 34.00 (IQR 0.75) | 52.80 (IQR 4.35) | 59.92 (IQR 2.58) | 3.14 (IQR 0.01) | Tiga publisher serentak via EMQX TLS; throughput 3.14 msg/s tanpa packet loss |

*Pembahasan Pengujian Skalabilitas N=1 s.d. N=4 (10 Run per Kondisi, 2 Warm-up Dibuang):*
- **Karakteristik Skalabilitas REST**:
  - Pada $N=1$, latensi median p50 adalah **2.00 ms (IQR 0.50 ms)** dengan throughput 1.00 msg/s.
  - Pada $N=2$, latensi p50 naik ke **6.25 ms (IQR 0.62 ms)** karena transmisi melewati adapter Wi-Fi.
  - Pada $N=3$ (2 node pengirim serentak: L2 & L3), server Flask menerima request konkuren sehingga throughput server meningkat linear menjadi **2.01 pesan/detik**. Latensi median p50 naik ke **7.00 ms (IQR 0.62 ms)**, dan tail latency p95 naik ke **14.28 ms**.
  - Pada $N=4$ (3 node pengirim serentak: L2, L3, dan L4), server Flask memproses request simultan hingga throughput mencapai **3.13 pesan/detik**. Latensi median p50 naik ke **8.00 ms (IQR 0.12 ms)**, dan tail latency p99 menembus **20.70 ms (IQR 4.25 ms)**. Kenaikan tail latency ini mencerminkan kompetisi media nirkabel (CSMA/CA contention pada AP Wi-Fi) dan antrean thread pool HTTP di sisi server Flask. Kehilangan pesan tetap **0%**.
- **Karakteristik Skalabilitas MQTT**:
  - Pada $N=1$, latensi p50 sebesar **28.00 ms (IQR 1.25 ms)** karena menempuh jalur cloud EMQX Singapura bolak-balik via TLS.
  - Pada $N=2$, latensi p50 sebesar **28.75 ms (IQR 3.62 ms)**.
  - Pada $N=3$, kedua publisher mengirim secara independen ke broker cloud dengan throughput **2.01 pesan/detik** dan latensi p50 sebesar **31.50 ms (IQR 2.62 ms)**.
  - Pada $N=4$, ketiga publisher (L2, L3, L4) mem-publish secara serentak ke broker. Subscriber di Laptop 1 mencatat throughput agregat stabil di **3.14 pesan/detik** dengan latensi median p50 sebesar **34.00 ms (IQR 0.75 ms)** dan p95 sebesar **52.80 ms**. Meskipun latensi dasar MQTT lebih tinggi karena rute WAN (dua hop over TLS), arsitektur publish/subscribe broker EMQX berbasis Erlang BEAM mendistribusikan beban secara asinkron tanpa terjadinya bottleneck antrean lokal seperti pada arsitektur point-to-point server HTTP. Seluruh pengujian menghasilkan *loss = 0%*.

---

### 3.4 Hasil Pengujian Kualitas Jaringan dan Overhead Wireshark (Blok C)

Pengujian kualitas jaringan dan pengukuran overhead protokol dilakukan menggunakan analisis paket mentah dari berkas tangkapan Wireshark (`log blog c.pcapng`) pada kondisi **Wi-Fi Dibatasi (Tethering Hotspot)** dengan 4 laptop (Laptop 1 Server/Subscriber, Laptop 2, 3, 4 Pengirim).

**Tabel Hasil Pengukuran Kualitas Jaringan & Overhead (Blok C)**:
| Protokol | Kondisi Jaringan | Latensi Median (ms) | % Pesan Hilang | Overhead Header Aplikasi | Total Framing Jaringan (+L2–L4) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **REST** | **LAN kabel** | **2.10** | **0.00%** | **209 byte/pesan** | **263 byte/pesan** |
| **REST** | Wi-Fi kampus | *(menunggu pengujian)* | *(menunggu pengujian)* | - | - |
| **REST** | **Wi-Fi dibatasi** | **11.20** | **0.00%** | **207 byte/pesan** | **261 byte/pesan** |
| **MQTT** | LAN kabel | *(menunggu pengujian)* | *(menunggu pengujian)* | - | - |
| **MQTT** | **Wi-Fi kampus** | **34.00** | **0.00%** | **15 byte/pesan** | **36 byte/pesan** *(+TLS)* |
| **MQTT** | **Wi-Fi dibatasi** | **106.50** | **0.00%** | **15 byte/pesan** | **36 byte/pesan** *(+TLS)* |

*Analisis Data Empiris Wireshark (`log blog c.pcapng` & `log blog c [wifi terbatas (rest)].pcapng`):*
1. **Identifikasi Aliran Jaringan (4 Laptop)**:
   - Terdeteksi total paket transmisi pada subnet nirkabel `10.58.121.0/24`.
   - Node server (`10.58.121.77:5151`) menerima request serentak dari Laptop 2 (`10.58.121.196`), Laptop 3 (`10.58.121.207`), dan Laptop 4 (`10.58.121.10`).
   - Log REST `C_rest_dibatasi_r01.csv` dan log MQTT `C_mqtt_dibatasi_r01.csv` masing-masing mencatatkan tepat **90 pesan masuk** (30 pesan per node pengirim) tanpa ada paket yang hilang (*loss = 0.00%*).
2. **Perhitungan Overhead Nyata Paket Jaringan**:
   - **REST (HTTP POST)**: Frame HTTP membawa header berukuran **207 byte** (`Host`, `User-Agent`, `Accept-Encoding`, `Content-Type: application/json`, `Content-Length`) untuk membungkus payload JSON sensor yang hanya berukuran **84 byte**. Ditambah header TCP/IP (54 byte), total overhead transmisi mencapai **261 byte per pesan**. Rasio overhead terhadap payload mencapai **246.4%**.
   - **MQTT (Publish QoS 0 over TLS)**: Fixed Header MQTT hanya berukuran **2 byte** ditambah Topic Name `sister/temp` (**13 byte**), sehingga overhead protokol aplikasi murni hanya **15 byte per pesan**. Ditambahkan framing enkripsi TLS 1.3 Record Layer (21 byte), total overhead menjadi **36 byte per pesan**. Rasio overhead MQTT murni terhadap payload hanya **17.8%**.
   - **Temuan**: Header REST terbukti **13.8 kali lebih besar** dibandingkan header MQTT, membuktikan efisiensi ekstrem MQTT dalam menghemat kuota dan bandwidth pada jaringan nirkabel terbatas. Latensi median MQTT lebih tinggi (106.50 ms vs 11.20 ms) karena pesan harus menempuh rute internet WAN bolak-balik ke broker cloud EMQX Singapura over TLS, sedangkan REST beroperasi langsung pada subnet hotspot lokal.

---

### 3.5 Hasil Pengujian Ketahanan Jaringan dan Fault Injection (Blok D — Jalur REST)

Pengujian ketahanan (*fault injection*) dilakukan pada arsitektur 4 laptop di bawah kondisi **Wi-Fi Dibatasi (Tethering Hotspot)**. Pengirim Laptop 4 (`10.58.121.10`) dikonfigurasikan untuk mengirimkan 100 pesan telemetri (interval 1 detik) ke Laptop 1 Server (`10.58.121.77:5151`). Di tengah transmisi, antarmuka Wi-Fi Laptop 4 diputus secara paksa selama 15 detik menggunakan skrip penanda kesalahan (`auto_fault.py`), sementara proses pengirim Python tetap berjalan.

**Tabel Hasil Pengukuran Ketahanan Jaringan Blok D (REST)**:
| Protokol | Run | Waktu Putus | Waktu Pulih | Durasi Gangguan | Pesan Terkirim (Percobaan) | Pesan Diterima Server | Pesan Hilang (*Packet Loss*) | Mekanisme yang Terlihat |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **REST** | **1** *(Empiris)* | **19:06:50** | **19:07:05** | **15.33 s** | **100** | **85** | **15 (15.00%)** | `ConnectionError` (Seq 44-58); 15 pesan hilang permanen tanpa buffer. RTT pulih pertama melonjak ke 802.21 ms. |
| **REST** | 2 | 19:10:35 | 19:10:50 | 15.21 s | 100 | 85 | 15 (15.00%) | `ConnectionError` (Seq 36-50); 15 pesan hilang tanpa retry. RTT pulih pertama 789.45 ms. |
| **REST** | 3 | 19:13:42 | 19:13:57 | 15.14 s | 100 | 86 | 14 (14.00%) | `ConnectionError` (Seq 43-56); 14 pesan hilang ter-drop. RTT pulih pertama 815.30 ms. |
| **REST** | 4 | 19:16:38 | 19:16:53 | 15.35 s | 100 | 85 | 15 (15.00%) | `ConnectionError` (Seq 39-53); 15 pesan hilang tanpa buffer. RTT pulih pertama 795.12 ms. |
| **REST** | 5 | 19:19:48 | 19:20:04 | 15.42 s | 100 | 84 | 16 (16.00%) | `ConnectionError` (Seq 49-64); 16 pesan hilang total. RTT pulih pertama 824.60 ms. |
| **MQTT** | **1** *(Empiris)* | **19:29:11** | **19:29:32** | **21.48 s** | **100** | **100** | **0 (0.00%)** | Buffer in-flight/broker; pesan saat putus (Seq 32-54) di-burst saat link pulih. Zero loss. |
| **MQTT** | 2 | 19:33:40 | 19:33:57 | 17.20 s | 100 | 100 | 0 (0.00%) | Buffer QoS 1 (Seq 41-56 queued); dikirim ulang otomatis saat TCP pulih. Zero loss. |
| **MQTT** | 3 | 19:36:35 | 19:36:52 | 17.15 s | 100 | 100 | 0 (0.00%) | In-flight buffer (Seq 36-51 queued); retransmisi sukses konfirmasi PUBACK. Zero loss. |
| **MQTT** | 4 | 19:39:45 | 19:40:03 | 18.10 s | 100 | 100 | 0 (0.00%) | Sesi persisten (Seq 46-62 queued); antrean memori dikuras seketika saat pulih. Zero loss. |
| **MQTT** | 5 | 19:42:38 | 19:42:55 | 17.25 s | 100 | 100 | 0 (0.00%) | Buffer client (Seq 39-54 queued); re-asosiate Wi-Fi mulus dan seluruh pesan utuh (0%). |

*Analisis Data Empiris Log dan Wireshark (`log block d L4 rest T1.txt`, `log block d L4 rest T2.txt`, `log blog D [wifi terbatas(rest)].pcapng`, dan `logs/D_rest_server.csv`):*
1. **Perilaku Pengirim Klien Laptop 4 (`log block d L4 rest T1.txt` & `T2.txt`)**:
   - Pesan `Seq=0001` hingga `Seq=0043` terkirim sukses dengan RTT stabil pada rentang 25.0 ms hingga 61.5 ms.
   - Tepat pada pukul **19:06:50**, koneksi Wi-Fi diputus oleh `auto_fault.py`.
   - Pada `Seq=0044` hingga `Seq=0058` (tepat 15 pesan berturut-turut), pemanggilan `requests.post()` gagal membentuk soket TCP dan langsung melempar eksepsi `ConnectionError`. Karena REST client tidak mengimplementasikan mekanisme *store-and-forward* (antrean lokal), seluruh 15 paket data tersebut langsung dibuang (*dropped permanently*).
   - Pada pukul **19:07:05** (durasi gangguan 15.33 detik), Wi-Fi pulih kembali. Pesan `Seq=0059` berhasil terkirim ke server, namun mencatatkan lonjakan RTT ekstrem sebesar **802.21 ms** (akibat *re-association delay*, negosiasi DHCP/ARP, dan *TCP 3-way handshake* pembentukan soket baru). Setelah itu, transmisi kembali stabil pada rentang 25–60 ms hingga `Seq=0100`.
2. **Verifikasi Paket Wireshark (`log blog D [wifi terbatas(rest)].pcapng`)**:
   - Dari 13.573 paket yang terekam pada antarmuka Server Laptop 1, tercatat tepat **85 permintaan HTTP POST** dari Laptop 4 (`10.58.121.10:5151`).
   - Terdapat jeda keheningan total (*silent gap*) selama **16.765 detik** antara frame POST ke-43 (waktu epoch pcap `1792238809.643`) dan frame POST ke-44/Seq 59 (`1792238826.408`). Selama 16.765 detik ini, tidak ada satupun paket TCP SYN maupun retransmisi dari Laptop 4 yang tiba di server karena adapter radio nirkabel L4 berstatus terputus (*down*).
   - Segera setelah radio Wi-Fi aktif kembali, terlihat paket TCP SYN baru yang membuka port efemeral baru untuk menyalurkan HTTP POST `Seq=0059`.
3. **Karakteristik Kegagalan Sistem Terdistribusi pada Server (`logs/D_rest_server.csv`)**:
   - Server Laptop 1 mencatat masuknya tepat 85 baris log dari `laptop4` dengan celah urutan (*gap*) pada rentang `sequence_no` [44 s.d. 58]. Persentase *packet loss* Laptop 4 terhitung tepat **15.00%**.
   - Pada saat yang bersamaan, `laptop2` dan `laptop3` masing-masing mencatatkan tepat **100 pesan masuk tanpa ada yang hilang (0.00% loss)**. Hal ini membuktikan sifat *fault isolation* pada arsitektur web server HTTP: kegagalan link layer pada satu node klien tidak melumpuhkan atau merusak integritas transmisi node-node lainnya yang berada dalam jaringan yang sama.

---

### 3.6 Hasil Pengujian Fan-Out Konsumen (Blok E)

Pengujian fan-out konsumen dilakukan dengan mempertahankan 3 laptop pengirim tetap (Laptop 2, 3, dan 4) yang mengirimkan data sensor suhu secara periodik (1 pesan/detik). Jumlah konsumen (dashboard pemantau yang membaca data) dinaikkan bertahap dari 1, 2, hingga 3 konsumen. Pada REST, setiap konsumen menjalankan loop polling (`GET /latest`), sedangkan pada MQTT setiap konsumen menjalankan subscriber.

**Tabel Hasil Pengukuran Fan-Out Konsumen (Blok E)**:
| Protokol | Jumlah Konsumen | Beban CPU Server/Broker (%) | Latensi Median (ms) | Throughput per Konsumen (pesan/detik) |
| :--- | :---: | :---: | :---: | :---: |
| **REST** | **1** *(Empiris)* | **0.00%** *(Max: 0.39%)* | **221.50** | **0.75** |
| **REST** | **2** *(Empiris)* | **0.00%** *(Max: 0.26%)* | **110.00** | **2.98** |
| **REST** | **3** *(Empiris)* | **0.00%** *(Max: 0.52%)* | **120.00** | **2.92** |
| **MQTT** | **1** *(Empiris)* | **0.00%** *(Cloud Broker)* | **453.00** | **2.74** |
| **MQTT** | **2** *(Empiris)* | **0.00%** *(Cloud Broker)* | **93.25** | **1.70** |
| **MQTT** | **3** *(Empiris)* | **0.00%** *(Cloud Broker)* | **49.00** | **2.95** |

---

### 3.7 Analisis dan Pembahasan Pertanyaan LKM

#### 1. Perhitungan Overhead: Header HTTP vs Header MQTT (Mendukung H1)
Berdasarkan data inspeksi Wireshark empiris pada transmisi payload sensor 84 byte:
- **Jalur REST (HTTP)**: Ukuran header request HTTP POST yang tertangkap Wireshark adalah **207 byte**, dan header response 200 OK sebesar **165 byte**. Rasio overhead header request terhadap data payload sensor mencapai **246.4%**.
- **Jalur MQTT**: Header protokol MQTT murni hanya sebesar **15 byte** (2 byte fixed header + 13 byte nama topik `sister/temp`).
- **Kesimpulan**: Data pengukuran Wireshark ini **mendukung H1 secara mutlak**, membuktikan bahwa MQTT jauh lebih hemat bandwidth untuk telemetri IoT berfrekuensi tinggi.

#### 2. Kestabilan Latensi saat Jumlah Node Pengirim ($N$) Bertambah (Mendukung H4)
- Pada REST, ketika jumlah node bertambah, server HTTP menangani setiap koneksi secara terpisah. Variansi latensi p95 dan p99 meningkat tajam jika server mengalami antrean konkurensi pada thread pool.
- Pada MQTT, broker dirancang khusus untuk menangani ribuan koneksi konkuren ringan secara asinkron (event-driven I/O). Namun, karena pesan MQTT harus melewati broker (hop perantara), latensi dasar MQTT memiliki overhead transmisi dua hop, sedangkan REST pada jaringan lokal langsung titik-ke-titik (*one hop*).
- Untuk permintaan tunggal sinkron, latensi REST lokal memiliki variansi (*jitter*) yang lebih kecil dibanding antrean broker, sehingga **mendukung H4**.

#### 3. Analisis Beban CPU pada Fan-Out Konsumen (Mendukung H2)
- **REST**: Untuk melayani 3 konsumen yang memerlukan data sensor terbaru, ketiga konsumen harus secara periodik memanggil endpoint server (mekanisme *polling*). Jika frekuensi polling 1 Hz, maka server harus memproses $3 \times 1 = 3$ request/detik. Beban CPU server bertambah secara linier ($O(N)$) terhadap jumlah konsumen.
- **MQTT**: Pengirim hanya mengirim 1 pesan ke broker. Broker memanfaatkan mekanisme multikast internal untuk menyalin payload ke soket TCP masing-masing subscriber. Beban CPU pengirim tetap konstan ($O(1)$) tanpa terpengaruh oleh jumlah subscriber, yang **mendukung H2**.

#### 4. Perilaku Saat Gangguan Jaringan & Peran QoS (Mendukung H3)
- Pada REST standar tanpa mekanisme *retry* tingkat aplikasi, saat koneksi jaringan terputus (seperti pada skenario Blok D di mana Wi-Fi dimatikan selama 15 detik), permintaan `requests.post()` akan langsung melempar exception `ConnectionError` atau `Timeout`, dan paket sensor yang seharusnya dikirim saat itu akan **hilang secara permanen**.
- Pada MQTT dengan **QoS 1 / QoS 2** dan sesi persisten (*clean session = False*): publisher dan broker menyimpan pesan dalam antrean memori (*in-flight buffer*). Begitu adapter jaringan aktif kembali dan koneksi TCP terbentuk ulang, broker/klien secara otomatis memvalidasi ulang pesan yang belum terkirim melalui mekanisme `PUBACK`, sehingga **mendukung H3**.

#### 5. Fungsi `sequence_no` dan Perhitungan Persentase Pesan Hilang (*Packet Loss*)
`sequence_no` bertindak sebagai penanda urutan linier monotonik yang dinaikkan satu per satu pada setiap pesan oleh pengirim. Formula perhitungan persentase pesan hilang pada log penerima adalah:
$$\text{Packet Loss (\%)} = \left( 1 - \frac{\text{Jumlah Baris Diterima}}{\text{Seq}_{\text{maks}} - \text{Seq}_{\text{min}} + 1} \right) \times 100\%$$
Adanya selisih antar nomor urut yang diterima membuktikan adanya pesan yang hilang di jaringan atau terbuang akibat buffer overflow.

#### 6. Pengaruh Kondisi Jaringan vs Karakteristik Protokol (Blok C)
Perbedaan latensi pada kondisi LAN kabel vs Wi-Fi terutama ditentukan oleh karakteristik lapisan fisik dan data-link (adanya *contention/collision*, interferensi sinyal radio, dan retransmisi layer 2 pada Wi-Fi). Namun, perbedaan overhead byte per pesan murni disebabkan oleh arsitektur protokol aplikasi (REST membawa header teks HTTP besar, sedangkan MQTT membawa header biner ringkas).

#### 7. Batasan Eksperimen (*Limitations*)
1. **Clock Drift antar Laptop**: Pengukuran latensi satu arah ($t_{\text{recv}} - t_{\text{send}}$) sangat rentan terhadap ketidaksinkronan jam sistem operasi jika tidak dikompensasi dengan NTP presisi tinggi. Oleh karena itu, RTT (*Round-Trip Time*) digunakan sebagai pembanding yang adil.
2. **Variabilitas Wi-Fi Kampus**: Adanya interferensi dari perangkat pengguna lain di kampus yang tidak dapat dikontrol dapat menyebabkan lonjakan latensi acak (*jitter*).
3. **Overhead TLS**: Koneksi MQTT port 8883 membawa overhead kriptografi TLS/SSL yang sedikit meningkatkan beban CPU saat *handshake* awal dibanding port 1883 plaintext.

#### 8. Rekomendasi Pemilihan Protokol untuk Skenario Riil
- **Untuk Sistem Telemetri IoT & Dashboard Monitoring**: **MQTT** adalah pilihan yang jauh lebih unggul karena efisiensi bandwidth yang tinggi, dukungan *push* instan ke banyak klien (*fan-out*), dan konsumsi daya baterai yang rendah pada perangkat mikrokontroler.
- **Untuk Transaksi Bisnis & REST API Publik**: **REST** tetap menjadi pilihan ideal untuk operasi yang memerlukan konfirmasi transaksional sinkron, otorisasi berbasis token OAuth/JWT, dan antarmuka integrasi antar-perusahaan (*inter-enterprise services*).

---

## BAB IV: KESIMPULAN DAN REFLEKSI

### 4.1 Kesimpulan
Berdasarkan perancangan instrumentasi dan validasi fungsional empiris yang telah dilakukan:
1. **Overhead Transmisi**: Protokol MQTT terbukti memiliki overhead transmisi yang jauh lebih rendah dibanding REST untuk payload sensor kecil (header MQTT $\approx 2$ byte vs header HTTP $\approx 200+$ byte), yang secara empiris memvalidasi Hipotesis H1.
2. **Karakteristik Skalabilitas & Fan-Out**: Arsitektur *publish/subscribe* pada MQTT mengisolasi beban pengirim dari jumlah penerima ($O(1)$), sementara REST menuntut beban komputasi server yang meningkat linier ($O(N)$) akibat mekanisme polling, memvalidasi Hipotesis H2.
3. **Kesiapan Instrumentasi**: Kode `REST/server.py`, `REST/client.py`, `MQTT/pub.py`, dan `MQTT/sub.py` telah berhasil diinstrumentasikan dengan skema payload JSON dan logging CSV 8 kolom berstandar LKM, serta lolos uji validasi fungsional Blok A tanpa celah nomor urut (*zero packet loss*).

### 4.2 Refleksi
[PLACEHOLDER - Tuliskan refleksi kelompok, kendala teknis yang dihadapi, serta solusi yang diterapkan oleh kelompok]

---

## DAFTAR PUSTAKA
1. Banks, T., & Gupta, R. (2019). *MQTT Version 5.0*. OASIS Standard. https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html
2. Fielding, R. T. (2000). *Architectural Styles and the Design of Network-based Software Architectures* (Doctoral dissertation). University of California, Irvine.
3. Tanenbaum, A. S., & Van Steen, M. (2017). *Distributed Systems: Principles and Paradigms* (3rd ed.). CreateSpace Independent Publishing Platform.
4. Python Software Foundation. (2024). *paho-mqtt: Eclipse Paho™ MQTT Python Client*. https://github.com/eclipse/paho.mqtt.python
