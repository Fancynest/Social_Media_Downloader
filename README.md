# Social Media Downloader Suite

Tool otomatisasi pengunduh media untuk YouTube, Instagram, X (Twitter), dan ThisVid berbasis Python. Ringan, cepat, dan mudah digunakan langsung melalui berkas batch (`.bat`) di Windows.

---

## Fitur Utama

### 1. YouTube Downloader
* **Kecepatan Maksimal:** Terhubung langsung ke CDN Google Global Cache (GGC) lokal, mengunduh dengan kecepatan penuh koneksi internet Anda.
* **Kualitas Terbaik (Full HD / 2K / 4K):** Otomatis memilih resolusi video dan audio terbaik lalu digabungkan menjadi format MP4 utuh via FFmpeg.
* **Dukungan Beragam Tautan:** Mendukung tautan video standar, Shorts, link pendek (`youtu.be`), maupun Playlist.
* **Bypass Batasan Usia (18+):** Mendukung pengunduhan video *Age-Restricted* dan *Members-only* melalui input cookies yang mudah.
* **Anti-Duplikat:** Video yang sudah pernah diunduh akan otomatis dilewati agar hemat waktu dan kuota.

### 2. Instagram Downloader
* **Filter Berdasarkan Keyword:** Memindai postingan dari profil target dan hanya mengunduh postingan yang takarirnya memuat kata kunci tertentu.
* **Unduh Banyak Link (Batch):** Mengunduh puluhan link Reel / Postingan sekaligus dari daftar tautan Notepad.
* **Mendukung Multi-Slide (Korsel):** Mengunduh seluruh slide foto/video secara lengkap beserta file teks takarirnya.
* **Smart Delay:** Dilengkapi jeda otomatis untuk menjaga koneksi aman dari limit Instagram.

### 3. Twitter / X Downloader
* **Foto Resolusi Asli:** Mengambil foto dengan format resolusi original (`?name=orig`) tanpa kompresi, mendukung 1 s/d 4 foto per tweet.
* **Video Kualitas Maksimal:** Otomatis memilih bitrate dan resolusi MP4 tertinggi.
* **Fast CDN Direct Resolver:** Mengunduh langsung melalui CDN tanpa perlu login atau membuka browser.
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
├── YouTube_Downloader/                   # Download Video, Shorts & Playlist YouTube
│   ├── BUKA_NOTEPAD_LINK.bat
│   ├── BUKA_NOTEPAD_COOKIE.bat
│   ├── DOWNLOAD_SEKARANG.bat
│   ├── link_youtube.txt
│   ├── input_cookie.txt
│   └── downloader.py
│
├── Instagram_Downloader/
│   ├── 1_Filter_Berdasarkan_Keyword/     # Download postingan IG berdasarkan kata kunci caption
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
├── Twitter_X_Downloader/                 # Download Foto & Video dari link X/Twitter
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

### YouTube (Video, Shorts & Playlist)
1. Buka `YouTube_Downloader/BUKA_NOTEPAD_LINK.bat`.
2. Tempelkan tautan video YouTube (1 baris 1 link), lalu simpan (`Ctrl+S`).
3. *(Opsional untuk video 18+/Restrict)*: Buka `YouTube_Downloader/BUKA_NOTEPAD_COOKIE.bat`, tempelkan cookies sesi login YouTube Anda, lalu simpan (`Ctrl+S`).
4. Jalankan `DOWNLOAD_SEKARANG.bat`. Media hasil unduhan akan tersimpan di folder `Hasil_Download\`.

### Instagram (Penyaring Kata Kunci)
1. Buka `Instagram_Downloader/1_Filter_Berdasarkan_Keyword/BUKA_INPUT_TARGET.bat`.
2. Masukkan akun target (bisa 1 atau banyak akun sekaligus dipisahkan koma) dan kata kunci yang ingin difilter.
3. Jalankan `JALANKAN_DOWNLOADER.bat`. Skrip akan memproses seluruh antrean akun secara berurutan.

### Instagram (Daftar Banyak Link)
1. Buka `Instagram_Downloader/2_Unduh_Banyak_Link/BUKA_NOTEPAD_LINK.bat`.
2. Tempelkan tautan Instagram (1 baris 1 link), lalu simpan (`Ctrl+S`).
3. Jalankan `DOWNLOAD_SEKARANG.bat`.

### Twitter / X (Foto & Video)
1. Buka `Twitter_X_Downloader/BUKA_NOTEPAD_LINK.bat`.
2. Tempelkan tautan postingan X/Twitter (1 baris 1 link), lalu simpan (`Ctrl+S`).
3. Jalankan `DOWNLOAD_SEKARANG.bat`.

### ThisVid (Video)
1. Buka `ThisVid_Downloader/BUKA_NOTEPAD_LINK.bat`.
2. Tempelkan tautan video ThisVid (1 baris 1 link), lalu simpan (`Ctrl+S`).
3. Jalankan `DOWNLOAD_SEKARANG.bat`.


