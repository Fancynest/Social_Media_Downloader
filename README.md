# Social Media Downloader Suite

Tool otomatisasi pengunduh media untuk YouTube, Instagram, X (Twitter), dan ThisVid berbasis Python. Ringan, cepat, dan mudah digunakan langsung melalui berkas batch (`.bat`) di Windows.

---

## Fitur Utama

### 1. YouTube Downloader
* **Kecepatan Maksimal:** Terhubung langsung ke CDN Google Global Cache (GGC) lokal, mengunduh dengan kecepatan penuh koneksi internet Anda.
* **Kualitas Terbaik (Full HD / 2K / 4K):** Otomatis memilih resolusi video dan audio terbaik lalu digabungkan menjadi format MP4 utuh via FFmpeg.
* **Modul 1 (Banyak Link):** Unduh massal dari daftar link video biasa, Shorts, atau Playlist.
* **Modul 2 (Channel & Rentang Waktu):** Unduh seluruh video dari channel YouTube (`https://www.youtube.com/@NamaChannel`) dengan filter tanggal upload (`DARI_TANGGAL` & `SAMPAI_TANGGAL`).
* **Bypass Batasan Usia (18+):** Mendukung video *Age-Restricted* dan *Members-only* melalui input cookies yang mudah.
* **Anti-Duplikat:** Video yang sudah pernah diunduh akan otomatis dilewati agar hemat kuota.

### 2. Instagram Downloader
* **Modul 1 (Filter Keyword):** Memindai postingan dari profil target dan hanya mengunduh postingan yang memuat kata kunci/hashtag tertentu.
* **Modul 2 (Banyak Link):** Mengunduh puluhan tautan Reel / Postingan sekaligus dari daftar tautan Notepad.
* **Modul 3 (Semua Postingan & Rentang Waktu):** Mengunduh seluruh postingan dari profil target dalam rentang tanggal tertentu (`DARI_TANGGAL` & `SAMPAI_TANGGAL`) tanpa perlu menyaring kata kunci.
* **Mendukung Multi-Slide (Korsel):** Mengunduh seluruh slide foto/video secara lengkap beserta file teks takarirnya.
* **Smart Delay:** Dilengkapi jeda otomatis untuk menjaga koneksi aman dari limit Instagram.

### 3. Twitter / X Downloader
* **Modul 1 (Banyak Link):** Unduh foto kualitas resolusi asli (`?name=orig`) dan video kualitas terbaik dari daftar tautan tweet.
* **Modul 2 (Profil & Rentang Waktu):** Unduh seluruh media feed dari profil target (`https://x.com/username`) dengan filter tanggal tweet (`DARI_TANGGAL` & `SAMPAI_TANGGAL`).
* **Fast Direct Resolver:** Mengunduh media langsung via CDN tanpa browser, serta mendukung cookies untuk konten sensitif/privat.
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
├── YouTube_Downloader/
│   ├── 1_Unduh_Banyak_Link/                  # Download massal Video, Shorts & Playlist
│   │   ├── BUKA_NOTEPAD_LINK.bat
│   │   ├── BUKA_NOTEPAD_COOKIE.bat
│   │   ├── DOWNLOAD_SEKARANG.bat
│   │   ├── link_youtube.txt
│   │   ├── input_cookie.txt
│   │   └── downloader.py
│   └── 2_Unduh_Channel_dan_Rentang_Waktu/    # Download semua video Channel + Rentang Waktu
│       ├── BUKA_NOTEPAD_TARGET.bat
│       ├── BUKA_NOTEPAD_COOKIE.bat
│       ├── DOWNLOAD_SEKARANG.bat
│       ├── target_channel.txt
│       ├── input_cookie.txt
│       └── channel_downloader.py
│
├── Instagram_Downloader/
│   ├── 1_Filter_Berdasarkan_Keyword/         # Download postingan IG via Filter Kata Kunci
│   │   ├── BUKA_INPUT_TARGET.bat
│   │   ├── JALANKAN_DOWNLOADER.bat
│   │   ├── LOGIN_AKUN.bat
│   │   ├── input_target.txt
│   │   └── ig_filter_downloader.py
│   ├── 2_Unduh_Banyak_Link/                  # Download massal dari daftar link Reels / Post
│   │   ├── BUKA_NOTEPAD_LINK.bat
│   │   ├── DOWNLOAD_SEKARANG.bat
│   │   ├── link_instagram.txt
│   │   └── ig_mass_downloader.py
│   └── 3_Unduh_Semua_Postingan_dan_Rentang_Waktu/ # Download SEMUA postingan profil + Rentang Waktu
│       ├── BUKA_INPUT_TARGET.bat
│       ├── JALANKAN_DOWNLOADER.bat
│       ├── LOGIN_AKUN.bat
│       ├── input_target.txt
│       └── ig_profile_downloader.py
│
├── Twitter_X_Downloader/
│   ├── 1_Unduh_Banyak_Link/                  # Download Foto & Video dari daftar link tweet
│   │   ├── BUKA_NOTEPAD_LINK.bat
│   │   ├── BUKA_NOTEPAD_COOKIE.bat
│   │   ├── DOWNLOAD_SEKARANG.bat
│   │   ├── link_video.txt
│   │   ├── input_cookie.txt
│   │   └── downloader.py
│   └── 2_Unduh_Profil_dan_Rentang_Waktu/     # Download semua media Profil + Rentang Waktu
│       ├── BUKA_NOTEPAD_TARGET.bat
│       ├── BUKA_NOTEPAD_COOKIE.bat
│       ├── DOWNLOAD_SEKARANG.bat
│       ├── target_profil.txt
│       ├── input_cookie.txt
│       └── profile_downloader.py
│
├── ThisVid_Downloader/
│   ├── BUKA_NOTEPAD_LINK.bat
│   ├── BUKA_NOTEPAD_COOKIE.bat
│   ├── DOWNLOAD_SEKARANG.bat
│   ├── link_video.txt
│   ├── input_cookie.txt
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

### YouTube Downloader
- **Unduh Video, Shorts, & Playlist Satuan/Massal:** Masuk ke folder `YouTube_Downloader/1_Unduh_Banyak_Link/`, buka `BUKA_NOTEPAD_LINK.bat`, tempelkan tautan video, lalu jalankan `DOWNLOAD_SEKARANG.bat`.
- **Unduh Seluruh Channel & Rentang Waktu:** Masuk ke folder `YouTube_Downloader/2_Unduh_Channel_dan_Rentang_Waktu/`, buka `BUKA_NOTEPAD_TARGET.bat`, isi `DARI_TANGGAL` & `SAMPAI_TANGGAL` (opsional) dan tempelkan link channel (`https://www.youtube.com/@NamaChannel`), lalu jalankan `DOWNLOAD_SEKARANG.bat`.

### Instagram Downloader
- **Filter Keyword / Caption:** Masuk ke `Instagram_Downloader/1_Filter_Berdasarkan_Keyword/`, buka `BUKA_INPUT_TARGET.bat`, isi target akun & kata kunci, lalu jalankan `JALANKAN_DOWNLOADER.bat`.
- **Unduh Banyak Link:** Masuk ke `Instagram_Downloader/2_Unduh_Banyak_Link/`, tempel tautan di `BUKA_NOTEPAD_LINK.bat`, lalu jalankan `DOWNLOAD_SEKARANG.bat`.
- **Unduh Semua Postingan & Rentang Waktu:** Masuk ke `Instagram_Downloader/3_Unduh_Semua_Postingan_dan_Rentang_Waktu/`, buka `BUKA_INPUT_TARGET.bat`, tentukan akun target serta rentang tanggal (`DARI_TANGGAL` dan `SAMPAI_TANGGAL`), lalu jalankan `JALANKAN_DOWNLOADER.bat`.

### Twitter / X Downloader
- **Unduh Tweet Satuan / Massal:** Masuk ke `Twitter_X_Downloader/1_Unduh_Banyak_Link/`, tempelkan link tweet di `BUKA_NOTEPAD_LINK.bat`, lalu jalankan `DOWNLOAD_SEKARANG.bat`.
- **Unduh Semua Media Profil & Rentang Waktu:** Masuk ke `Twitter_X_Downloader/2_Unduh_Profil_dan_Rentang_Waktu/`, buka `BUKA_NOTEPAD_TARGET.bat`, tentukan rentang tanggal dan tempel link profil (`https://x.com/username`), lalu jalankan `DOWNLOAD_SEKARANG.bat`.

### ThisVid Downloader
1. Buka `ThisVid_Downloader/BUKA_NOTEPAD_LINK.bat`.
2. Tempelkan tautan video ThisVid (1 baris 1 link), lalu simpan (`Ctrl+S`).
3. Jalankan `DOWNLOAD_SEKARANG.bat`.
