**LEMBAR KERJA MAHASISWA (LKM)**  
Sensor Suhu Terdistribusi: Perbandingan MQTT dan REST

| Komponen | Keterangan |
| :---- | :---- |
| Mata kuliah | Sistem Terdistribusi (S2) |
| Topik | Eksperimen empiris MQTT (publish/subscribe) vs REST (request/response) |
| Berkas praktikum | REST/server.py, REST/client.py, MQTT/pub.py, MQTT/sub.py |
| Estimasi waktu | 3–4 minggu (sesuai jadwal kelompok) |
| Topologi yang dipakai | (  ) 1 laptop     (  ) 2 laptop     (  ) 3 laptop     (  ) 4 laptop |
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
| H1 | Overhead per pesan MQTT lebih rendah dari REST untuk payload kecil. |  |  |  |
| H2 | Pada fan-out, beban sisi pengirim MQTT relatif konstan terhadap jumlah konsumen; REST naik seiring konsumen. |  |  |  |
| H3 | MQTT (QoS 1/2 \+ sesi persisten) lebih tangguh terhadap gangguan jaringan sesaat dibanding REST tanpa retry. |  |  |  |
| H4 | Untuk permintaan tunggal sinkron, latensi round-trip REST lebih dapat diprediksi (variansi lebih kecil). |  |  |  |

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
| REST | 2 |  |  |  |  |  |
| REST | 3 |  |  |  |  |  |
| REST | 4 |  |  |  |  |  |
| MQTT | 2 |  |  |  |  |  |
| MQTT | 3 |  |  |  |  |  |
| MQTT | 4 |  |  |  |  |  |

## **Langkah 4 — Blok C: Kualitas jaringan dan overhead (4 laptop)**

Bandingkan tiga kondisi: LAN kabel, Wi-Fi kampus, dan Wi-Fi dibatasi. Untuk kondisi lintas jaringan, ekspos REST server dengan ngrok agar jalur REST sebanding dengan MQTT yang sudah lewat cloud broker. Tangkap paket dengan Wireshark untuk mengukur overhead.

| Protokol | Kondisi jaringan | Latensi median (ms) | % pesan hilang | Overhead (byte/pesan) |
| :---- | :---- | :---- | :---- | :---- |
| REST | LAN kabel |  |  |  |
| REST | Wi-Fi kampus |  |  |  |
| REST | Wi-Fi dibatasi |  |  |  |
| MQTT | LAN kabel |  |  |  |
| MQTT | Wi-Fi kampus |  |  |  |
| MQTT | Wi-Fi dibatasi |  |  |  |

## **Langkah 5 — Blok D: Ketahanan (fault injection, 4 laptop)**

1\.	Pada tengah sesi, matikan adapter Wi-Fi laptop pengirim selama 15 detik lewat pengaturan OS. Jangan mematikan proses Python.

2\.	Catat waktu putus dan waktu pulih. Ulangi minimal 5 kali untuk tiap protokol.

3\.	Isi tabel berikut:

| Protokol | Run | Waktu putus | Waktu pulih | Pesan terkirim | Pesan diterima | Pesan hilang | Mekanisme yang terlihat |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| REST | 1 |  |  |  |  |  |  |
| REST | 2 |  |  |  |  |  |  |
| REST | 3 |  |  |  |  |  |  |
| REST | 4 |  |  |  |  |  |  |
| REST | 5 |  |  |  |  |  |  |
| MQTT | 1 |  |  |  |  |  |  |
| MQTT | 2 |  |  |  |  |  |  |
| MQTT | 3 |  |  |  |  |  |  |
| MQTT | 4 |  |  |  |  |  |  |
| MQTT | 5 |  |  |  |  |  |  |

## **Langkah 6 — Blok E: Fan-out konsumen (3 node pengirim tetap)**

Tambahkan konsumen (dashboard) satu per satu: 1, lalu 2, lalu 3\. Pada REST, setiap konsumen menjalankan loop polling. Pada MQTT, setiap konsumen menjalankan subscriber.

| Protokol | Jumlah konsumen | Beban CPU server/broker (%) | Latensi median (ms) | Throughput per konsumen (pesan/detik) |
| :---- | :---- | :---- | :---- | :---- |
| REST | 1 |  |  |  |
| REST | 2 |  |  |  |
| REST | 3 |  |  |  |
| MQTT | 1 |  |  |  |
| MQTT | 2 |  |  |  |
| MQTT | 3 |  |  |  |

## **Langkah 7 — Blok F (opsional): QoS MQTT (4 laptop; Wi-Fi dibatasi)**

| QoS | Latensi median (ms) | % pesan hilang | Catatan |
| :---- | :---- | :---- | :---- |
| 0 |  |  |  |
| 1 |  |  |  |
| 2 |  |  |  |

# **F. Pertanyaan Analisis**

1\.	Hitung overhead per pesan dari hasil Wireshark: header HTTP dibanding header MQTT. Apakah H1 didukung? Jelaskan dengan angka dari tabel Blok C.

2\.	Pada Blok B, bagaimana latensi p50, p95, dan p99 berubah saat N bertambah? Protokol mana yang lebih stabil, dan apakah ini mendukung H4?

3\.	Pada Blok E, mengapa beban CPU di sisi REST server naik saat jumlah konsumen bertambah, sementara beban di sisi broker relatif tetap? Kaitkan dengan mekanisme polling dan push.

4\.	Pada Blok D, apa yang terjadi pada pesan saat node terputus? Apakah H3 didukung? Jelaskan peran QoS dan sesi persisten.

5\.	Mengapa sequence\_no diperlukan? Bagaimana kelompok Anda menghitung persentase pesan hilang dari log?

6\.	Apakah perbedaan latensi antar-kondisi jaringan di Blok C lebih disebabkan oleh protokol atau oleh kondisi jaringan? Jelaskan.

7\.	Sebutkan batasan eksperimen yang tidak bisa dikontrol (spesifikasi laptop, variabilitas Wi-Fi, jam yang tidak sinkron, atau faktor implementasi). Bagaimana pengaruhnya terhadap kesimpulan?

8\.	Dalam skenario Anda sendiri (misalnya IoT, aplikasi mobile, atau dashboard web), protokol mana yang akan Anda pilih? Sebutkan minimal dua alasan yang didukung data kelompok Anda.

# **G. Kesimpulan**

*Tuliskan 4–5 kalimat yang merangkum hasil kelompok terhadap H1–H4.*

# **H. Refleksi**

*Bagian paling sulit dan cara kelompok mengatasinya:*

# **I. Checklist Pengumpulan**

* \[  \]  Kode termodifikasi di repositori kelompok (tanpa berkas .env)  
* \[  \]  Log CSV mentah untuk setiap blok eksperimen  
* \[  \]  Notebook atau skrip analisis yang mereproduksi seluruh grafik dari log mentah  
* \[  \]  Laporan tertulis 6–10 halaman: pendahuluan dan hipotesis, metodologi, hasil, diskusi, batasan, kesimpulan  
* \[  \]  Demo langsung di kelas dengan laptop kelompok (minimal 2 laptop, disarankan 4\)

**Rubrik penilaian**

| Aspek | Bobot |
| :---- | :---- |
| Ketepatan instrumentasi dan reproduksibilitas (log lengkap, dapat dijalankan ulang) | 20% |
| Kedalaman analisis kuantitatif (statistik, bukan angka tunggal) | 30% |
| Keterkaitan hasil dengan hipotesis dan literatur | 25% |
| Kejujuran dan kejelasan pembahasan batasan | 10% |
| Demo dan penjelasan lisan | 15% |

