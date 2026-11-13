# Social Media Downloader Suite

Tool otomatisasi pengunduh media untuk YouTube, Instagram, X (Twitter), dan ThisVid berbasis Python. Ringan, cepat, dan mudah digunakan langsung melalui berkas batch (`.bat`) di Windows.

---

## Fitur Utama

### 1. YouTube Downloader
* **Kecepatan Maksimal:** Terhubung langsung ke CDN Google Global Cache (GGC) lokal, mengunduh dengan kecepatan penuh koneksi internet Anda.
* **Kualitas Terbaik (Full HD / 2K / 4K):** Otomatis memilih resolusi video dan audio terbaik lalu digabungkan menjadi format MP4 utuh via FFmpeg.
* **Unduh Seluruh Channel / Playlist / Akun:** Cukup masukkan link profil channel (`https://www.youtube.com/@NamaChannel`), playlist, atau video satuan.
* **Filter Rentang Waktu (Tanggal):** Mendukung filter tanggal rilis/upload (`DARI_TANGGAL` dan `SAMPAI_TANGGAL`) dalam berkas konfigurasi.
* **Bypass Batasan Usia (18+):** Mendukung pengunduhan video *Age-Restricted* dan *Members-only* melalui input cookies yang mudah.
* **Anti-Duplikat:** Video yang sudah pernah diunduh akan otomatis dilewati agar hemat waktu dan kuota.

### 2. Instagram Downloader
* **Unduh Semua Postingan atau Berdasarkan Keyword:** Dapat memindai seluruh postingan akun target tanpa filter kata kunci, atau hanya menyaring postingan dengan kata kunci/hashtag tertentu.
* **Filter Rentang Waktu (Tanggal):** Dilengkapi batas `DARI_TANGGAL` dan `SAMPAI_TANGGAL` untuk mengunduh postingan dalam periode spesifik secara otomatis.
* **Unduh Banyak Link (Batch):** Mengunduh puluhan tautan Reel / Postingan sekaligus dari daftar tautan Notepad.
* **Mendukung Multi-Slide (Korsel):** Mengunduh seluruh slide foto/video secara lengkap beserta file teks takarirnya.
* **Smart Delay:** Dilengkapi jeda otomatis untuk menjaga koneksi aman dari limit Instagram.

### 3. Twitter / X Downloader
* **Unduh Tweet Satuan atau Seluruh Profil Pengguna:** Cukup masukkan tautan tweet atau tautan profil akun (`https://x.com/username` atau `https://twitter.com/username`).
* **Filter Rentang Waktu (Tanggal):** Mendukung penyaringan rentang tanggal (`DARI_TANGGAL` dan `SAMPAI_TANGGAL`) untuk pengunduhan profil.
* **Foto Resolusi Asli:** Mengambil foto dengan format resolusi original (`?name=orig`) tanpa kompresi, mendukung 1 s/d 4 foto per tweet.
* **Video Kualitas Maksimal:** Otomatis memilih bitrate dan resolusi MP4 tertinggi.
* **Fast Direct Resolver:** Mengunduh media publik langsung melalui engine CDN tanpa browser, serta mendukung cookies untuk konten sensitif/privat.
* **Anti-Duplikat:** Otomatis mendeteksi media yang sudah pernah diunduh agar hemat kuota.

### 4. ThisVid Downloader
* **Batch Download Massal:** Unduh banyak video sekaligus dari daftar tautan di Notepad.
* **Kualitas Video & Audio Maksimal:** Otomatis memilih resolusi terbaik dan menggabungkan audio/video menjadi MP4 utuh.
* **Auto-DoH Anti-Sensor:** Melewati pembajakan DNS ISP (Internet Sehat) secara otomatis.
* **Anti-Duplikat:** Melewati video yang sudah pernah berhasil diunduh.

---

## Struktur Direktori

```text
Social_Media_Downloader/
├── YouTube_Downloader/                   # Download Video, Shorts, Playlist & Seluruh Channel
│   ├── BUKA_NOTEPAD_LINK.bat
│   ├── BUKA_NOTEPAD_COOKIE.bat
│   ├── DOWNLOAD_SEKARANG.bat
│   ├── link_youtube.txt
│   ├── input_cookie.txt
│   └── downloader.py
│
├── Instagram_Downloader/
│   ├── 1_Filter_Berdasarkan_Keyword/     # Download postingan IG (Semua / Filter Keyword + Filter Tanggal)
│   │   ├── BUKA_INPUT_TARGET.bat
│   │   ├── JALANKAN_DOWNLOADER.bat
│   │   ├── LOGIN_AKUN.bat
│   │   ├── input_target.txt
│   │   └── ig_filter_downloader.py
│   └── 2_Unduh_Banyak_Link/              # Download massal Reels/Post IG dari daftar link
│       ├── BUKA_NOTEPAD_LINK.bat
│       ├── DOWNLOAD_SEKARANG.bat
│       ├── link_instagram.txt
│       └── ig_mass_downloader.py
│
├── Twitter_X_Downloader/                 # Download Foto & Video dari link Postingan atau Seluruh Akun X
│   ├── BUKA_NOTEPAD_LINK.bat
│   ├── BUKA_NOTEPAD_COOKIE.bat
│   ├── DOWNLOAD_SEKARANG.bat
│   ├── link_video.txt
│   └── downloader.py
│
├── ThisVid_Downloader/                   # Download Video dari link ThisVid
│   ├── BUKA_NOTEPAD_LINK.bat
│   ├── BUKA_NOTEPAD_COOKIE.bat
│   ├── DOWNLOAD_SEKARANG.bat
│   ├── link_video.txt
│   └── downloader.py
│
├── requirements.txt
└── README.md
```

---

## Instalasi & Persiapan

1. Pastikan **Python 3.10+** sudah terpasang di komputer Anda.
2. Pasang library yang dibutuhkan melalui terminal / CMD:
   ```bash
   pip install -r requirements.txt
   ```

---

## Cara Penggunaan

### YouTube (Video, Shorts, Playlist, & Channel)
1. Buka `YouTube_Downloader/BUKA_NOTEPAD_LINK.bat`.
2. Anda dapat mengatur rentang waktu (opsional) pada bagian atas:
   ```text
   DARI_TANGGAL=2024-01-01
   SAMPAI_TANGGAL=2024-12-31
   ```
   *(Biarkan kosong jika ingin mengunduh semua tanggal)*.
3. Tempelkan tautan video atau tautan channel (misal: `https://www.youtube.com/@NamaChannel`), lalu simpan (`Ctrl+S`).
4. *(Opsional untuk video 18+/Restrict)*: Buka `YouTube_Downloader/BUKA_NOTEPAD_COOKIE.bat`, tempelkan cookies sesi login YouTube Anda, lalu simpan (`Ctrl+S`).
5. Jalankan `DOWNLOAD_SEKARANG.bat`. Media hasil unduhan akan tersimpan di folder `Hasil_Download\`.

### Instagram (Semua Postingan & Filter Tanggal / Keyword)
1. Buka `Instagram_Downloader/1_Filter_Berdasarkan_Keyword/BUKA_INPUT_TARGET.bat`.
2. Atur target:
   - `TARGET_ACCOUNTS`: nama akun target (misal: `natgeo`).
   - `DARI_TANGGAL` & `SAMPAI_TANGGAL`: atur rentang tanggal (misal: `2024-01-01` s/d `2024-06-30`), atau kosongkan untuk semua.
   - `KEYWORDS`: kata kunci pencarian takarir, atau **KOSONGKAN** jika ingin mengunduh **SEMUA** postingan akun target.
3. Jalankan `JALANKAN_DOWNLOADER.bat`.

### Instagram (Daftar Banyak Link)
1. Buka `Instagram_Downloader/2_Unduh_Banyak_Link/BUKA_NOTEPAD_LINK.bat`.
2. Tempelkan tautan Instagram (1 baris 1 link), lalu simpan (`Ctrl+S`).
3. Jalankan `DOWNLOAD_SEKARANG.bat`.

### Twitter / X (Postingan Satuan & Seluruh Akun / Profil)
1. Buka `Twitter_X_Downloader/BUKA_NOTEPAD_LINK.bat`.
2. Anda dapat mengatur rentang waktu (opsional) pada baris:
   ```text
   DARI_TANGGAL=2024-01-01
   SAMPAI_TANGGAL=2024-12-31
   ```
   *(Biarkan kosong jika ingin mengunduh semua tanggal)*.
3. Tempelkan tautan postingan atau link profil pengguna (misal: `https://x.com/elonmusk`), lalu simpan (`Ctrl+S`).
4. Jalankan `DOWNLOAD_SEKARANG.bat`.

### ThisVid (Video)
1. Buka `ThisVid_Downloader/BUKA_NOTEPAD_LINK.bat`.
2. Tempelkan tautan video ThisVid (1 baris 1 link), lalu simpan (`Ctrl+S`).
3. Jalankan `DOWNLOAD_SEKARANG.bat`.
