# Instagram Downloader Suite

Koleksi tool otomatisasi untuk mengunduh konten dari Instagram (Foto, Video, Reels, dan Korsel).

## Struktur Direktori

```text
Instagram_Downloader/
├── 1_Filter_Berdasarkan_Keyword/
│   ├── BUKA_INPUT_TARGET.bat      # Buka file konfigurasi target
│   ├── JALANKAN_DOWNLOADER.bat    # Jalankan downloader filter
│   ├── LOGIN_AKUN.bat             # Login akun (opsional)
│   ├── input_target.txt           # Parameter akun, keyword, dan limit
│   ├── ig_filter_downloader.py    # Script utama filter
│   └── Hasil_Download/            # Folder output media
└── 2_Unduh_Banyak_Link/
    ├── BUKA_NOTEPAD_LINK.bat      # Buka file daftar link
    ├── DOWNLOAD_SEKARANG.bat      # Jalankan downloader massal
    ├── link_instagram.txt         # Daftar URL target
    ├── ig_mass_downloader.py      # Script utama batch downloader
    └── Hasil_Download/            # Folder output media
```

## Prasyarat & Instalasi

- Python 3.10+
- Library yang dibutuhkan:
  ```bash
  pip install instaloader yt-dlp
  ```

## Cara Penggunaan

### Modul 1: Filter Berdasarkan Keyword
1. Buka `BUKA_INPUT_TARGET.bat`.
2. Isi `TARGET_AKUN` (bisa 1 atau banyak akun sekaligus dipisahkan koma), `KEYWORDS` (pisahkan koma), dan `MAKSIMAL_POST` (0 = semua).
3. Jalankan `JALANKAN_DOWNLOADER.bat`. Skrip akan memproses seluruh antrean akun secara berurutan.

### Modul 2: Unduh Banyak Link
1. Buka `BUKA_NOTEPAD_LINK.bat`.
2. Tempelkan link postingan/reel Instagram (satu link per baris).
3. Jalankan `DOWNLOAD_SEKARANG.bat`.

## Troubleshooting

- **Rate Limit (429 Too Many Requests):**
  Jika memakai hotspot HP, aktifkan Mode Pesawat selama 5 detik lalu matikan untuk mendapatkan IP baru.
- **Akun Privat:**
  Gunakan `LOGIN_AKUN.bat` pada modul filter untuk autentikasi menggunakan akun sekunder.
