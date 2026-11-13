# Instagram Downloader Suite

Koleksi tool otomatisasi untuk mengunduh konten dari Instagram (Foto, Video, Reels, dan Korsel).

## Struktur Direktori

```text
Instagram_Downloader/
├── 1_Filter_Berdasarkan_Keyword/              # Filter postingan berdasarkan keyword/hashtag caption
│   ├── BUKA_INPUT_TARGET.bat                  # Buka konfigurasi target & keyword
│   ├── JALANKAN_DOWNLOADER.bat                # Jalankan downloader filter
│   ├── LOGIN_AKUN.bat                         # Login akun (opsional)
│   ├── input_target.txt                       # Parameter target, keyword, hashtag
│   ├── ig_filter_downloader.py                # Script filter downloader
│   └── Hasil_Download/                        # Folder output media
│
├── 2_Unduh_Banyak_Link/                       # Unduh massal banyak link Reels / Postingan
│   ├── BUKA_NOTEPAD_LINK.bat                  # Buka file daftar link
│   ├── DOWNLOAD_SEKARANG.bat                  # Jalankan downloader batch link
│   ├── link_instagram.txt                     # Daftar tautan Instagram
│   ├── ig_mass_downloader.py                  # Script batch downloader
│   └── Hasil_Download/                        # Folder output media
│
└── 3_Unduh_Semua_Postingan_dan_Rentang_Waktu/ # Unduh semua postingan profil + filter rentang tanggal
    ├── BUKA_INPUT_TARGET.bat                  # Buka konfigurasi akun target & tanggal
    ├── JALANKAN_DOWNLOADER.bat                # Jalankan downloader profil
    ├── LOGIN_AKUN.bat                         # Login akun (opsional)
    ├── input_target.txt                       # Parameter target & tanggal (YYYY-MM-DD)
    ├── ig_profile_downloader.py               # Script profil downloader
    └── Hasil_Download/                        # Folder output media
```

## Prasyarat & Instalasi

- Python 3.10+
- Library yang dibutuhkan:
  ```bash
  pip install -r ../requirements.txt
  ```

## Cara Penggunaan

### Modul 1: Filter Berdasarkan Keyword
1. Buka `1_Filter_Berdasarkan_Keyword/BUKA_INPUT_TARGET.bat`.
2. Isi `TARGET_AKUN`, `KEYWORDS`, `HASHTAGS`, dan batas tanggal jika diperlukan.
3. Jalankan `JALANKAN_DOWNLOADER.bat`.

### Modul 2: Unduh Banyak Link
1. Buka `2_Unduh_Banyak_Link/BUKA_NOTEPAD_LINK.bat`.
2. Tempelkan link postingan/reel Instagram (satu link per baris).
3. Jalankan `DOWNLOAD_SEKARANG.bat`.

### Modul 3: Unduh Semua Postingan & Rentang Waktu
1. Buka `3_Unduh_Semua_Postingan_dan_Rentang_Waktu/BUKA_INPUT_TARGET.bat`.
2. Masukkan akun target pada `TARGET_AKUN`.
3. Tentukan rentang tanggal pada `DARI_TANGGAL` dan `SAMPAI_TANGGAL` (format `YYYY-MM-DD`, kosongkan jika ingin mengunduh semua).
4. Jalankan `JALANKAN_DOWNLOADER.bat`.

## Troubleshooting

- **Rate Limit (429 Too Many Requests):**
  Jika memakai hotspot HP, aktifkan Mode Pesawat selama 5 detik lalu matikan untuk mendapatkan IP baru.
- **Akun Privat:**
  Gunakan `LOGIN_AKUN.bat` atau masukkan `sessionid` pada `input_cookie.txt`.
