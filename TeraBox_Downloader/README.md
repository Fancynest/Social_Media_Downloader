# TeraBox Master Downloader (16-Thread Accelerated)

Modul pengunduh berkas video, foto, dan dokumen dari TeraBox dengan kualitas asli (*Master Original / Lossless bit-for-bit*), bypass proteksi bot Cloudflare menggunakan `curl_cffi` Chrome TLS fingerprint, dan akselerasi unduhan 16 thread simultan via `aria2c`.

## Fitur Utama
- **Original Master Quality**: Mengunduh langsung file mentah (*dlink*) yang diunggah pemilik aslinya tanpa kompresi ulang atau penurunan bitrate (1080p, 4K, dsb).
- **Auto Bypass & Dynamic jsToken**: Mengambil sesi dan `jsToken` dinamis dari landing page secara otomatis untuk mengatasi proteksi Cloudflare dan verifikasi API TeraBox.
- **16 Parallel Threads**: Membagi file unduhan menjadi 16 koneksi fragmentasi simultan dengan `aria2c` untuk kecepatan maksimal.
- **Fallback Streaming**: Dilengkapi mesin pengunduh chunked Python bawaan dengan fitur *Range resume* jika `aria2c` tidak tersedia.
- **Dukungan Domain Lengkap**: Mendukung `terabox.com`, `teraboxapp.com`, `1024tera.com`, `terafileshare.com`, `mirrobox.com`, `nephobox.com`, serta link bersandi (`pwd`).
- **Pencegah Unduhan Ganda**: Mencatat file yang selesai ke `download_history.txt`.

## Cara Penggunaan
1. Klik ganda `BUKA_INPUT_LINK.bat` dan tempelkan link TeraBox.
2. (Opsional untuk file besar >500MB) Klik `BUKA_INPUT_COOKIE.bat` dan isi cookie `ndus=...`.
3. Klik ganda `UNDUH_TERABOX.bat`.
4. Berkas tersimpan di folder `Hasil_Download/`.
