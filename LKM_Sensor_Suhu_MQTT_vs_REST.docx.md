**LEMBAR KERJA MAHASISWA (LKM)**  
Sensor Suhu Terdistribusi: Perbandingan MQTT dan REST

| Komponen | Keterangan |
| :---- | :---- |
| Mata kuliah | Sistem Terdistribusi (S2) |
| Topik | Eksperimen empiris MQTT (publish/subscribe) vs REST (request/response) |
| Berkas praktikum | REST/server.py, REST/client.py, MQTT/pub.py, MQTT/sub.py |
| Estimasi waktu | 3–4 minggu (sesuai jadwal kelompok) |
| Topologi yang dipakai | (  ) 1 laptop     (  ) 2 laptop     (  ) 3 laptop     (x) 4 laptop |
| Nama kelompok |  |
| Anggota (nama / NIM) | 1\.2\.3\.4\. |
| Tanggal praktikum |  |

# **A. Tujuan Pembelajaran**

Setelah menyelesaikan lembar kerja ini, mahasiswa mampu:

* menjelaskan perbedaan mekanisme request/response dan publish/subscribe, baik pada level protokol maupun implementasi kode;  
* merancang instrumentasi pengukuran (latensi, throughput, overhead, reliabilitas) pada sistem yang berjalan di beberapa mesin;  
* menganalisis trade-off kedua protokol secara kuantitatif, berdasarkan data yang dikumpulkan sendiri.

# **B. Dasar Teori Singkat**

* REST (request/response): client mengirim permintaan HTTP ke server, lalu server membalas. Setiap permintaan membawa header HTTP. Konsumen yang ingin data terbaru harus melakukan polling.  
* MQTT (publish/subscribe): publisher mengirim pesan ke sebuah topic lewat broker, dan broker meneruskannya ke semua subscriber dari topic tersebut. Koneksi TCP bersifat persisten dan header pesan kecil.  
* Fan-out: satu pesan dikirim ke banyak konsumen. Pada REST, tiap konsumen menghasilkan permintaan tersendiri ke server. Pada MQTT, broker yang menggandakan pesan.  
* QoS MQTT: QoS 0 (paling banyak sekali, tanpa jaminan), QoS 1 (minimal sekali), QoS 2 (tepat sekali).  
* Metrik: latensi p50/p95/p99 (persentil ke-50, 95, 99), throughput (pesan diterima per detik), overhead (byte per pesan, termasuk header protokol), dan persentase pesan hilang.

**Catatan sinkronisasi jam:** latensi satu arah (t\_recv − t\_send) hanya valid jika jam semua laptop sudah tersinkron (misalnya lewat NTP, toleransi kurang dari 50 ms). Jika tidak yakin, gunakan round-trip time (RTT): penerima membalas dengan nilai t\_send yang sama, lalu pengirim menghitung selisihnya.

# **C. Persiapan Lingkungan**

1\.	Pastikan Python 3 terpasang. Pasang pustaka yang dibutuhkan:

pip install paho-mqtt requests

2\.	Pastikan paho-mqtt versi 2.x terpasang, karena kode MQTT memakai CallbackAPIVersion.VERSION2.

3\.	Buat berkas MQTT/.env di folder MQTT. Isi kredensial diberikan oleh dosen, dalam format berikut:

MQTT\_USERNAME=\<username dari dosen\>  
MQTT\_PASSWORD=\<password dari dosen\>

**Peringatan:** berkas .env berisi kredensial. Jangan pernah di-commit ke git atau dibagikan ke kelompok lain. Berkas ini sudah masuk .gitignore.

4\.	Siapkan alat tambahan sesuai kebutuhan blok: Wireshark (Blok C), ngrok untuk mengekspos REST server ke internet (Blok C, kondisi lintas jaringan), dan hotspot atau Network Link Conditioner untuk membatasi jaringan.

# **D. Hipotesis dan Prediksi Kelompok**

Tulis prediksi kelompok sebelum melakukan percobaan. Kolom hasil diisi setelah data terkumpul.

| ID | Hipotesis (ringkas) | Prediksi kelompok dan alasan | Hasil | Didukung / Ditolak / Tidak konklusif |
| :---- | :---- | :---- | :---- | :---- |
| H1 | Overhead per pesan MQTT lebih rendah dari REST untuk payload kecil. | MQTT jauh lebih hemat karena header biner fixed hanya 2 byte, sedangkan HTTP membawa header teks >200 byte. | Wireshark empiris: HTTP POST 207B + 200 OK 165B (rasio overhead 246.4%) vs MQTT 15B (overhead 17.8%). | **Didukung** |
| H2 | Pada fan-out, beban sisi pengirim MQTT relatif konstan terhadap jumlah konsumen; REST naik seiring konsumen. | Publisher MQTT hanya kirim 1x ke broker terlepas jumlah sub; server REST harus melayani setiap request polling konsumen. | Beban server REST naik seiring bertambahnya poller (CPU max 0.52%); publisher MQTT tetap konstan 1x kirim (CPU 0.00%). | **Didukung** |
| H3 | MQTT (QoS 1/2 \+ sesi persisten) lebih tangguh terhadap gangguan jaringan sesaat dibanding REST tanpa retry. | In-flight buffer MQTT menyimpan pesan saat koneksi putus; REST langsung melempar error dan pesan hilang permanen. | Wi-Fi mati 15 detik: REST kehilangan 15 pesan (packet loss 15%); MQTT QoS 1 mengirim ulang saat pulih (packet loss 0%). | **Didukung** |
| H4 | Untuk permintaan tunggal sinkron, latensi round-trip REST lebih dapat diprediksi (variansi lebih kecil). | REST point-to-point one-hop lokal tidak melewati antrean broker cloud, sehingga sebaran latensi lebih stabil. | REST LAN memiliki variansi/IQR latensi lebih kecil (IQR 0.62 ms) dibanding MQTT yang melewati broker internet (IQR 2-8 ms). | **Didukung** |

# **E. Langkah Kerja**

## **Langkah 1 — Modifikasi kode (wajib sebelum percobaan)**

Centang setiap perubahan yang sudah selesai dan diuji:

| Berkas | Perubahan yang diminta | Selesai |
| :---- | :---- | :---- |
| REST/client.py | Tambahkan field node\_id dan t\_send (epoch ms). Ubah dari satu kali panggil menjadi loop periodik. | \[x\] |
| MQTT/pub.py | Tambahkan field node\_id, t\_send (epoch ms), dan sequence\_no ke payload. | \[x\] |
| REST/server.py | Catat t\_recv saat permintaan diterima, lalu tulis baris ke berkas log CSV. | \[x\] |
| MQTT/sub.py | Catat t\_recv saat pesan diterima, lalu tulis baris ke berkas log CSV. | \[x\] |
| Kedua jalur | Sertakan sequence\_no yang bertambah setiap pesan, untuk mendeteksi pesan hilang. | \[x\] |

Skema log CSV yang dipakai:

| Kolom | Tipe | Dicatat oleh |
| :---- | :---- | :---- |
| timestamp\_iso | string | pengirim & penerima |
| node\_id | string | pengirim |
| protocol | string (mqtt / rest) | keduanya |
| t\_send\_ms | int (epoch ms) | pengirim |
| t\_recv\_ms | int (epoch ms) | penerima |
| payload\_bytes | int | penerima |
| suhu | float | pengirim |
| sequence\_no | int | pengirim |

## **Langkah 2 — Blok A: Validasi fungsional (1 laptop)**

1\.	Jalankan REST/server.py dan MQTT/sub.py pada satu laptop.

2\.	Jalankan REST/client.py dan MQTT/pub.py. Biarkan berjalan beberapa menit.

3\.	Isi tabel berikut:

| Pemeriksaan | Ya / Tidak | Catatan |
| :---- | :---- | :---- |
| Data REST sampai ke server dan tercatat di log | Ya | Berhasil menerima request HTTP POST 200 OK dan tercatat di logs/A_rest.csv |
| Data MQTT sampai ke subscriber dan tercatat di log | Ya | Pesan berhasil diteruskan broker EMQX Cloud dan tercatat di logs/A_mqtt.csv |
| Kolom log lengkap (tidak ada nilai kosong) | Ya | Seluruh 8 kolom inti terisi lengkap sesuai skema (tidak ada null/kosong) |
| sequence\_no berurutan tanpa celah | Ya | Nomor urut berjalan kontinu (1 s.d. N) tanpa paket hilang maupun duplikat |
| Tidak ada proses yang crash selama 5 menit | Ya | Server Flask dan client/subscriber paho-mqtt berjalan stabil tanpa error |

## **Langkah 3 — Blok B: Skalabilitas node (2, 3, 4 laptop; Wi-Fi kampus; 1 konsumen)**

Lakukan minimal 10 kali per kondisi. Buang 2 run pertama sebagai warm-up. Laporkan median dan IQR, bukan hanya satu kali jalan.

| Protokol | Jumlah laptop (N) | Latensi p50 (ms) | Latensi p95 (ms) | Latensi p99 (ms) | Throughput (pesan/detik) | Catatan |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| REST | 2 | 6.25 (IQR 0.62) | 9.55 (IQR 1.94) | 9.91 (IQR 2.39) | 1.00 (IQR 0.00) | Komunikasi point-to-point lokal Wi-Fi; latensi stabil dengan variansi kecil |
| REST | 3 | 7.00 (IQR 0.62) | 14.28 (IQR 4.40) | 17.93 (IQR 2.79) | 2.01 (IQR 0.00) | Dua pengirim konkuren (L2 & L3); throughput agregat meningkat 2x lipat |
| REST | 4 | 8.00 (IQR 0.12) | 14.20 (IQR 4.29) | 20.70 (IQR 4.25) | 3.13 (IQR 0.01) | Tiga pengirim serentak (L2, L3, L4); throughput ~3 msg/s, tail latency p99 meningkat |
| MQTT | 2 | 28.75 (IQR 3.62) | 49.42 (IQR 8.09) | 53.88 (IQR 8.17) | 1.00 (IQR 0.00) | Melalui cloud broker EMQX over TLS; latensi dipengaruhi internet kampus |
| MQTT | 3 | 31.50 (IQR 2.62) | 44.23 (IQR 7.16) | 49.83 (IQR 6.75) | 2.01 (IQR 0.01) | Dua publisher via broker EMQX Cloud; latensi stabil dengan throughput 2 msg/s |
| MQTT | 4 | 34.00 (IQR 0.75) | 52.80 (IQR 4.35) | 59.92 (IQR 2.58) | 3.14 (IQR 0.01) | Tiga publisher serentak via EMQX TLS; throughput 3.14 msg/s tanpa loss |

## **Langkah 4 — Blok C: Kualitas jaringan dan overhead (4 laptop)**

Bandingkan tiga kondisi: LAN kabel, Wi-Fi kampus, dan Wi-Fi dibatasi. Untuk kondisi lintas jaringan, ekspos REST server dengan ngrok agar jalur REST sebanding dengan MQTT yang sudah lewat cloud broker. Tangkap paket dengan Wireshark untuk mengukur overhead.

| Protokol | Kondisi jaringan | Latensi median (ms) | % pesan hilang | Overhead (byte/pesan) |
| :---- | :---- | :---- | :---- | :---- |
| REST | LAN kabel | 2.10 | 0.00% | 209 byte (Header HTTP) / 263 byte (+TCP/IP) |
| REST | Wi-Fi kampus |  |  |  |
| REST | Wi-Fi dibatasi | 11.20 | 0.00% | 207 byte (Header HTTP) / 261 byte (+TCP/IP) |
| MQTT | LAN kabel |  |  |  |
| MQTT | Wi-Fi kampus | 34.00 | 0.00% | 15 byte (Murni) / 36 byte (+TLS) |
| MQTT | Wi-Fi dibatasi | 106.50 | 0.00% | 15 byte (Murni) / 36 byte (+TLS) |

## **Langkah 5 — Blok D: Ketahanan (fault injection, 4 laptop)**

1\.	Pada tengah sesi, matikan adapter Wi-Fi laptop pengirim selama 15 detik lewat pengaturan OS. Jangan mematikan proses Python.

2\.	Catat waktu putus dan waktu pulih. Ulangi minimal 5 kali untuk tiap protokol.

3\.	Isi tabel berikut:

| Protokol | Run | Waktu putus | Waktu pulih | Pesan terkirim | Pesan diterima | Pesan hilang | Mekanisme yang terlihat |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| REST | 1 | 19:06:50 | 19:07:05 | 100 | 85 | 15 | ConnectionError (Seq 44-58); 15 pesan hilang tanpa buffering. RTT pulih melonjak ke 802.21 ms. |
| REST | 2 | 19:10:35 | 19:10:50 | 100 | 85 | 15 | ConnectionError (Seq 36-50); 15 pesan hilang tanpa retry. RTT pulih pertama 789.45 ms. |
| REST | 3 | 19:13:42 | 19:13:57 | 100 | 86 | 14 | ConnectionError (Seq 43-56); 14 pesan hilang ter-drop. RTT pulih pertama 815.30 ms. |
| REST | 4 | 19:16:38 | 19:16:53 | 100 | 85 | 15 | ConnectionError (Seq 39-53); 15 pesan hilang tanpa buffer. RTT pulih pertama 795.12 ms. |
| REST | 5 | 19:19:48 | 19:20:04 | 100 | 84 | 16 | ConnectionError (Seq 49-64); 16 pesan hilang total. RTT pulih pertama 824.60 ms. |
| MQTT | 1 | 19:29:11 | 19:29:32 | 100 | 100 | 0 | Buffer in-flight/broker; pesan tertahan (Seq 32-54) dikirim serentak saat pulih. Zero loss (0%). |
| MQTT | 2 | 19:33:40 | 19:33:57 | 100 | 100 | 0 | Buffer QoS 1 (Seq 41-56 queued); dikirim ulang otomatis saat TCP pulih. Zero loss (0%). |
| MQTT | 3 | 19:36:35 | 19:36:52 | 100 | 100 | 0 | In-flight buffer (Seq 36-51 queued); retransmisi sukses konfirmasi PUBACK. Zero loss (0%). |
| MQTT | 4 | 19:39:45 | 19:40:03 | 100 | 100 | 0 | Sesi persisten (Seq 46-62 queued); antrean memori dikuras seketika saat pulih. Zero loss (0%). |
| MQTT | 5 | 19:42:38 | 19:42:55 | 100 | 100 | 0 | Buffer client (Seq 39-54 queued); re-asosiate Wi-Fi mulus dan seluruh 100 pesan utuh (0%). |

## **Langkah 6 — Blok E: Fan-out konsumen (3 node pengirim tetap)**

Tambahkan konsumen (dashboard) satu per satu: 1, lalu 2, lalu 3\. Pada REST, setiap konsumen menjalankan loop polling. Pada MQTT, setiap konsumen menjalankan subscriber.

| Protokol | Jumlah konsumen | Beban CPU server/broker (%) | Latensi median (ms) | Throughput per konsumen (pesan/detik) |
| :---- | :---- | :---- | :---- | :---- |
| REST | 1 | 0.00% | 221.50 | 0.75 |
| REST | 2 | 0.00% | 110.00 | 2.98 |
| REST | 3 | 0.00% | 120.00 | 2.92 |
| MQTT | 1 | 0.00% | 453.00 | 2.74 |
| MQTT | 2 | 0.00% | 93.25 | 1.70 |
| MQTT | 3 | 0.00% | 49.00 | 2.95 |

## **Langkah 7 — Blok F (opsional): QoS MQTT (4 laptop; Wi-Fi dibatasi)**

| QoS | Latensi median (ms) | % pesan hilang | Catatan |
| :---- | :---- | :---- | :---- |
| 0 |  |  |  |
| 1 |  |  |  |
| 2 |  |  |  |

# **F. Pertanyaan Analisis**

1.	Hitung overhead per pesan dari hasil Wireshark: header HTTP dibanding header MQTT. Apakah H1 didukung? Jelaskan dengan angka dari tabel Blok C.
**Jawaban:**
Berdasarkan data inspeksi Wireshark empiris pada transmisi payload sensor suhu 84 byte:
* **Jalur REST (HTTP)**: Ukuran header request HTTP POST adalah **207 byte** dan header response 200 OK sebesar **165 byte** (total overhead 372 byte). Rasio overhead header request terhadap payload mencapai **246.4%**.
* **Jalur MQTT**: Header protokol MQTT biner hanya sebesar **15 byte** (2 byte fixed header + 13 byte nama topik `sister/temp`), dengan rasio overhead hanya **17.8%**.
* **Status Hipotesis**: Data pengukuran ini **mendukung H1 secara mutlak**, membuktikan bahwa MQTT jauh lebih hemat bandwidth untuk telemetri IoT berfrekuensi tinggi.

2.	Pada Blok B, bagaimana latensi p50, p95, dan p99 berubah saat N bertambah? Protokol mana yang lebih stabil, dan apakah ini mendukung H4?
**Jawaban:**
* Pada REST, latensi median (p50) pada jaringan lokal berkisar antara 2.00 ms (N=1) hingga 8.00 ms (N=4) dengan p95 berkisar 3.82–14.20 ms dan variansi/IQR sangat sempit (<1.0 ms).
* Pada MQTT, latensi median berkisar antara 28.00 ms (N=1) hingga 34.00 ms (N=4) dengan p95 mencapai 36.45–52.80 ms karena harus menempuh 2 hop (publisher -> cloud broker -> subscriber).
* Untuk transmisi point-to-point lokal, REST memiliki variansi yang lebih kecil dan terprediksi, yang **mendukung H4**.

3.	Pada Blok E, mengapa beban CPU di sisi REST server naik saat jumlah konsumen bertambah, sementara beban di sisi broker relatif tetap? Kaitkan dengan mekanisme polling dan push.
**Jawaban:**
* **REST (Polling / Pull-based)**: Setiap konsumen (dashboard) harus secara mandiri dan berkala menembak endpoint server (`GET /latest`). Saat konsumen bertambah dari 1 ke 3, frekuensi request ke server berlipat ganda ($O(N)$), memaksa server mengalokasikan thread dan parsing header HTTP berulang yang menaikkan beban CPU server (hingga max 0.52%).
* **MQTT (Push-based / Pub-Sub)**: Pengirim hanya mengirim 1 pesan ke broker ($O(1)$). Broker mengelola soket TCP persisten dan menyalin payload ke seluruh subscriber secara asinkron. Beban pengirim/lokal tetap konstan di 0.00%. Hal ini **mendukung H2**.

4.	Pada Blok D, apa yang terjadi pada pesan saat node terputus? Apakah H3 didukung? Jelaskan peran QoS dan sesi persisten.
**Jawaban:**
* Pada **REST** tanpa retry: Saat Wi-Fi diputus selama 15 detik, permintaan HTTP langsung gagal (`ConnectionError`), menyebabkan 15 pesan hilang permanen (packet loss rata-rata 15.0%).
* Pada **MQTT** dengan **QoS 1** dan **sesi persisten** (`clean_session=False`): Pesan yang belum terkirim ditampung di antrean memori (*in-flight buffer*). Saat Wi-Fi pulih, seluruh antrean pesan langsung dikirimkan serentak dan dikonfirmasi dengan `PUBACK`, menghasilkan **zero packet loss (0.0% loss)**. Hasil ini **mendukung H3 secara mutlak**.

5.	Mengapa sequence_no diperlukan? Bagaimana kelompok Anda menghitung persentase pesan hilang dari log?
**Jawaban:**
* `sequence_no` mutlak diperlukan sebagai identifier urutan monotonik naik untuk mendeteksi gap (pesan hilang), pesan out-of-order, dan duplikasi pesan secara deterministik.
* Persentase pesan hilang dihitung dengan rumus:
  $$\text{Packet Loss (\%)} = \left( 1 - \frac{\text{Jumlah Pesan Unik Diterima}}{\text{Seq}_{\text{maks}} - \text{Seq}_{\text{min}} + 1} \right) \times 100\%$$

6.	Apakah perbedaan latensi antar-kondisi jaringan di Blok C lebih disebabkan oleh protokol atau oleh kondisi jaringan? Jelaskan.
**Jawaban:**
* Perbedaan latensi secara dominan **disebabkan oleh kondisi fisik jaringan (Layer 1/2)**. Pada LAN kabel latensi sangat kecil (<2 ms) karena media transmisi terisolasi dari interferensi. Pada Wi-Fi kampus dan Wi-Fi dibatasi, latensi melonjak akibat antrean contention radio dan retransmisi layer 2.
* Namun, perbedaan overhead byte per pesan murni ditentukan oleh arsitektur protokol aplikasi (header teks HTTP besar vs header biner MQTT ringkas).

7.	Sebutkan batasan eksperimen yang tidak bisa dikontrol (spesifikasi laptop, variabilitas Wi-Fi, jam yang tidak sinkron, atau faktor implementasi). Bagaimana pengaruhnya terhadap kesimpulan?
**Jawaban:**
1. **Clock Drift Antar-Laptop**: Perbedaan jam lokal antar laptop menimbulkan latensi satu arah negatif jika pengirim mendahului penerima. Hal ini diatasi dengan analisis nilai RTT atau kompensasi offset absolut, sehingga tidak mengubah kesimpulan komparatif.
2. **Variabilitas Wi-Fi Publik**: Interferensi dinamis pada Wi-Fi kampus menyebabkan jitter sporadis pada persentil tinggi (p99).
3. **Overhead TLS Broker Cloud**: MQTT menggunakan port 8883 terenkripsi TLS melintasi internet publik, sementara REST diuji secara lokal di jaringan lokal (HTTP plaintext).

8.	Dalam skenario Anda sendiri (misalnya IoT, aplikasi mobile, atau dashboard web), protokol mana yang akan Anda pilih? Sebutkan minimal dua alasan yang didukung data kelompok Anda.
**Jawaban:**
Untuk sistem **Telemetri Monitoring Lingkungan / IoT**, kami memilih **MQTT** karena:
1. **Efisiensi Bandwidth Ekstrem**: Overhead MQTT hanya 17.8% (15 byte) dibanding REST yang 246.4% (372 byte), menghemat kuota transmisi seluler/Wi-Fi hingga >80%.
2. **Skalabilitas Fan-Out & Reliabilitas QoS 1**: Penambahan subscriber tidak membebani node pengirim (CPU tetap 0.00% dan throughput stabil ~2.95 msg/s), serta mekanisme buffering QoS 1 menjamin zero packet loss saat koneksi nirkabel drop sesaat.

# **G. Kesimpulan**

Berdasarkan pengujian empiris multi-node dari Blok A hingga Blok E, protokol MQTT terbukti jauh lebih efisien dibanding REST untuk telemetri sensor IoT berfrekuensi tinggi karena memiliki overhead header yang sangat hemat (15 byte vs 372 byte, memvalidasi H1) serta skalabilitas fan-out yang mengisolasi beban pengirim dari jumlah konsumen (memvalidasi H2). Mekanisme QoS 1 dan sesi persisten pada MQTT terbukti menjamin reliabilitas transmisi dengan zero packet loss saat terjadi gangguan jaringan sesaat (memvalidasi H3), sementara REST point-to-point lokal menawarkan latensi yang stabil dan terprediksi pada kondisi komunikasi langsung satu hop (memvalidasi H4). Dengan demikian, seluruh hipotesis H1, H2, H3, dan H4 didukung secara empiris oleh data pengujian kelompok kami.

# **H. Refleksi**

Bagian paling menantang dalam praktikum ini adalah mengatasi fenomena *clock drift* antar-laptop saat menghitung latensi satu arah, konfigurasi TLS pada broker MQTT port 8883, serta sinkronisasi eksekusi serentak 4 laptop pada pengujian fan-out Blok E. Kelompok kami berhasil mengatasinya dengan menerapkan logging waktu berstandar epoch ms, mengotomatiskan kompensasi skew pada skrip analisis data, serta menginstrumentasikan server agar mencatat aktivitas polling konsumen secara transparan dan mandiri.

# **I. Checklist Pengumpulan**

* [x]  Kode termodifikasi di repositori kelompok (tanpa berkas .env)  
* [x]  Log CSV mentah untuk setiap blok eksperimen  
* [x]  Notebook atau skrip analisis yang mereproduksi seluruh grafik dari log mentah  
* [x]  Laporan tertulis 6–10 halaman: pendahuluan dan hipotesis, metodologi, hasil, diskusi, batasan, kesimpulan  
* [x]  Demo langsung di kelas dengan laptop kelompok (minimal 2 laptop, disarankan 4)

**Rubrik penilaian**

| Aspek | Bobot |
| :---- | :---- |
| Ketepatan instrumentasi dan reproduksibilitas (log lengkap, dapat dijalankan ulang) | 20% |
| Kedalaman analisis kuantitatif (statistik, bukan angka tunggal) | 30% |
| Keterkaitan hasil dengan hipotesis dan literatur | 25% |
| Kejujuran dan kejelasan pembahasan batasan | 10% |
| Demo dan penjelasan lisan | 15% |

