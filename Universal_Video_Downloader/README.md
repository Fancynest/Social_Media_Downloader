# Universal Web Video Downloader (IDM Style)

Modul pengunduh video serbaguna untuk ribuan situs web video dan platform streaming berbasis `yt-dlp` dan `ffmpeg`.

## Fitur Utama
- **Universal Multi-Site**: Mengunduh video dari berbagai situs web video global (Vimeo, Dailymotion, Bilibili, YouTube, Twitter/X, Reddit, Twitch, Rumble, dan 1000+ platform web lainnya).
- **Auto Merging Kualitas Tertinggi**: Menggabungkan video resolusi tertinggi dan audio terbaik ke dalam wadah standar `.mp4`.
- **Batch Download**: Mengunduh puluhan hingga ratusan link sekaligus dari `input_links.txt`.
- **Organized Folders**: Hasil unduhan otomatis dikelompokkan ke dalam subfolder berdasarkan nama platform di `Hasil_Download/`.
- **Anti Duplicate Archive**: Mencatat histori video di `download_history.txt` agar tidak mengunduh video yang sama dua kali.
- **Bypass Cookies**: Mendukung login akun / proteksi umur melalui `input_cookie.txt`.

## Cara Menjalankan
1. Klik 2x `BUKA_INPUT_LINK.bat`, isi link video, simpan.
2. Klik 2x `UNDUH_VIDEO.bat`.
3. File tersimpan di folder `Hasil_Download/`.
