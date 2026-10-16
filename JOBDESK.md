# JOBDESK per Laptop — LKM Sensor Suhu MQTT vs REST

Ganti `<IP-L1>` dengan IP LAN/WiFi L1 sesuai kondisi yang diukur.
Semua perintah dari root folder `LKM_MQTT_REST_kerja/`.
Aturan kondisi jaringan (Blok C): satu kondisi = satu interface aktif
(LAN kabel → WiFi MATI; WiFi → kabel CABUT).

## L1 — SERVER + LOGGER (anjing penjaga data)

**Persiapan:**
- `pip install -r requirements.txt`, taruh `MQTT/.env`, `python3 MQTT/check_mqtt.py` → SUKSES
- Install Wireshark, siapkan filter `host <IP-L1>`, pastikan port 5151 bebas + firewall izinkan
- Buat folder `logs/`, jadi pengumpul CSV dari semua laptop

**Blok A:** terminal 1 `python3 REST/server.py --log logs/A_rest.csv`,
terminal 2 `python3 MQTT/sub.py --log logs/A_mqtt.csv`. Jangan matikan sampai L2 selesai.

**Blok B/C:** server + subscriber tetap jalan per kondisi N=2,3,4 dan per kondisi
jaringan; ganti `--log` tiap run (`logs/B_rest_N2.csv`, `logs/C_kabel_rest.csv`, dst).
Catat jam mulai/selesai tiap kondisi.

**Blok D:** tetap standby; catat waktu putus/pulih yang diteriakkan operator L4.

**Blok E:** server tetap; untuk REST catat CPU (`top`) tiap jumlah konsumen 1/2/3.

**Blok F:** subscriber dengan `--qos 0/1/2 --log logs/F_qos<n>.csv` bergantian.

**Demo:** tampilkan dashboard EMQX + grafik `analyze.py` + 1 contoh Wireshark.

## L2 — PENGIRIM UTAMA

**Persiapan:** sama (install, `.env`, cek SUKSES, ping `<IP-L1>` lolos).

**Blok A:** terminal 1
`python3 REST/client.py --server http://<IP-L1>:5151 --node-id laptop2 --count 60`
terminal 2 `python3 MQTT/pub.py --node-id laptop2 --count 60`.
Kirim `client_rest.csv` ke L1, rename `logs/A_laptop2_rest.csv`.

**Blok B/C/D/F:** ulangi pola yang sama per kondisi (ganti `--log` +
`--node-id laptop2` tetap); Blok D: JANGAN jadi korban pertama (L4 dulu).

**Blok E (REST):** jadi poller-1 tetap di semua tahap 1/2/3 konsumen.

**Demo:** jalankan 1x publish live + tunjukkan RTT di terminal.

## L3 — PENGIRIM/KONSUMEN-2

**Persiapan:** sama. Latihan matikan/hidupkan WiFi via OS (bukan kill Python).

**Blok A:** idle/standby (boleh ikut cek koneksi saja).

**Blok B:** masuk saat N=3 dan N=4:
`python3 REST/client.py --server http://<IP-L1>:5151 --node-id laptop3 --count 100 --log logs/B_laptop3_N<n>.csv`
dan `python3 MQTT/pub.py --node-id laptop3 --count 100` di waktu yang sama.

**Blok C:** ikut semua 3 kondisi jaringan dengan pola yang sama.

**Blok D:** korban cadangan (L4 utama). Saat giliran: matikan WiFi 15 detik,
teriakkan "PUTUS ... PULIH ...", hidupkan lagi. JANGAN tutup terminal Python.

**Blok E:** jadi konsumen-2 (subscriber kedua / poller kedua).

**Demo:** operator fault-injection (peragakan putus 15 detik).

## L4 — PENGIRIM/KONSUMEN-3 + KORBAn FAULT UTAMA (kamu)

**Persiapan:** sama. WAJIB latihan: lokasi tombol/matikan WiFi di OS-mu,
stopwatch/HP untuk hitung 15 detik, dan latihan mengetik perintah buta
(karena WiFi mati = tidak bisa browsing contekan).

**Blok A:** idle/standby.

**Blok B:** masuk saat N=4 saja, pola sama dengan `--node-id laptop4`.

**Blok C:** ikut semua 3 kondisi jaringan.

**Blok D (PERAN UTAMA):** korban pertama dan utama, 5x per protokol:
1. Pastikan publisher-mu sedang jalan.
2. Teriakkan "PUTUS <jam:menit:detik>", matikan WiFi.
3. Hitung 15 detik (stopwatch), hidupkan WiFi, teriakkan "PULIH <jam>".
4. L1 mencatat; ulangi 5x REST + 5x MQTT.
Aturan keras: proses Python TETAP JALAN selama WiFi mati (jangan Ctrl+C,
jangan tutup laptop/lid-sleep — atur power agar tidak sleep).

**Blok E:** jadi konsumen-3 (subscriber ketiga / poller ketiga).

**Demo:** tunjukkan Tabel Blok D + jelaskan apa yang terjadi pada pesan saat putus.

## Aturan bersama (4 laptop)

1. `sequence_no` tidak boleh di-reset manual di tengah blok.
2. Tiap run: 10x ukur + buang 2 warm-up (Blok B); 5x (Blok D).
3. Nama file log baku `logs/<blok>_<protokol>_<kondisi>.csv`, setor ke L1 tiap selesai blok.
4. `Ctrl+C` bersih di akhir tiap run; JANGAN tutup terminal paksa.
5. `.env` tidak pernah masuk git/chat publik; masalah kredensial lapor privat.
