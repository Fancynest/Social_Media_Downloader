# X (Twitter) Media Downloader

Tool otomatisasi berkecepatan tinggi untuk mengunduh Video dan Foto dari X (Twitter) tanpa perlu login.

## Fitur Utama

- **Foto & Video:** Mengunduh video (bitrate tertinggi) dan foto (resolusi asli `?name=orig`).
- **Multi-Media:** Mendukung unduhan postingan dengan 1-4 foto sekaligus.
- **Fast CDN Resolver:** Menggunakan direct API resolver tanpa overhead peramban.
- **Deduplikasi Otomatis:** Mencatat riwayat unduhan pada `download_history.txt` agar tidak mendownload ulang file yang sama.

## Struktur Direktori

```text
Downloader_Video_X/
├── BUKA_NOTEPAD_LINK.bat   # Buka notepad daftar link
├── DOWNLOAD_SEKARANG.bat   # Jalankan downloader
├── link_video.txt          # Daftar URL video/foto target
├── downloader.py           # Script utama pengunduh
├── download_history.txt    # Cache riwayat download
└── Hasil_Download/         # Folder output media
```

## Prasyarat & Instalasi

- Python 3.10+
- yt-dlp (opsional sebagai fallback):
  ```bash
  pip install yt-dlp
  ```

## Cara Penggunaan

1. Klik 2x `BUKA_NOTEPAD_LINK.bat`.
2. Tempelkan URL postingan X/Twitter (satu baris satu link).
3. Simpan (`Ctrl+S`), lalu klik 2x `DOWNLOAD_SEKARANG.bat`.
4. Hasil unduhan otomatis tersimpan di folder `Hasil_Download/`.
