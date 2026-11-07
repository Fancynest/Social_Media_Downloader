# Social Media Downloader Suite

Tool otomatisasi pengunduh media untuk Instagram dan X (Twitter) berbasis Python. Ringan, cepat, dan mudah digunakan langsung melalui berkas batch (`.bat`) di Windows.

---

## Fitur Utama

### 1. Instagram Downloader
* **Filter Berdasarkan Keyword:** Memindai postingan dari profil target dan hanya mengunduh postingan yang takarirnya memuat kata kunci tertentu.
* **Unduh Banyak Link (Batch):** Mengunduh puluhan link Reel / Postingan sekaligus dari daftar tautan Notepad.
* **Mendukung Multi-Slide (Korsel):** Mengunduh seluruh slide foto/video secara lengkap beserta file teks takarirnya.
* **Smart Delay:** Dilengkapi jeda otomatis untuk menjaga koneksi aman dari limit Instagram.

### 2. Twitter / X Downloader
* **Foto Resolusi Asli:** Mengambil foto dengan format resolusi original (`?name=orig`) tanpa kompresi, mendukung 1 s/d 4 foto per tweet.
* **Video Kualitas Maksimal:** Otomatis memilih bitrate dan resolusi MP4 tertinggi.
* **Fast CDN Direct Resolver:** Mengunduh langsung melalui CDN tanpa perlu login atau membuka browser.
* **Anti-Duplikat:** Otomatis mendeteksi media yang sudah pernah diunduh agar hemat kuota.

---

## Struktur Direktori

```text
Social_Media_Downloader/
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
