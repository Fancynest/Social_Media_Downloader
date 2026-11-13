# YouTube Media Downloader

Pengunduh massal video YouTube berkualitas tinggi berbasis Python, `yt-dlp`, dan `ffmpeg`. Mendukung video standar, YouTube Shorts, video panjang, dan playlist dengan penggabungan audio/video otomatis menjadi MP4, serta dukungan bypass video batasan usia (18+) via cookies.

## Berkas & Struktur

* **`BUKA_NOTEPAD_LINK.bat`**: Membuka `link_youtube.txt` untuk mengisi daftar tautan.
* **`BUKA_NOTEPAD_COOKIE.bat`**: Membuka `input_cookie.txt` untuk menempelkan cookies autentikasi (opsional, untuk konten 18+).
* **`DOWNLOAD_SEKARANG.bat`**: Menjalankan pengunduhan otomatis ke folder `Hasil_Download`.
* **`link_youtube.txt`**: Berkas daftar URL YouTube yang ingin diunduh.
* **`input_cookie.txt`**: Berkas penyimpanan cookies sesi login YouTube.
* **`download_history.txt`**: Catatan riwayat media agar tidak diunduh ganda.
* **`Hasil_Download/`**: Direktori penyimpanan berkas video MP4.
