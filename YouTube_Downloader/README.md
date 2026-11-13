# YouTube Downloader Suite

Koleksi tool otomatisasi untuk mengunduh video, Shorts, Playlist, dan seluruh Channel YouTube.

## Struktur Direktori

```text
YouTube_Downloader/
├── 1_Unduh_Banyak_Link/                 # Unduh massal dari daftar link (Video, Shorts, Playlist)
│   ├── BUKA_NOTEPAD_LINK.bat            # Buka file daftar link
│   ├── BUKA_NOTEPAD_COOKIE.bat          # Buka file input cookies (opsional)
│   ├── DOWNLOAD_SEKARANG.bat            # Jalankan downloader
│   ├── link_youtube.txt                 # Daftar link video
│   ├── input_cookie.txt                 # File cookies login
│   ├── downloader.py                    # Script batch downloader
│   └── Hasil_Download/                  # Folder output video
│
└── 2_Unduh_Channel_dan_Rentang_Waktu/   # Unduh semua video dari Channel + filter rentang tanggal
    ├── BUKA_NOTEPAD_TARGET.bat          # Buka konfigurasi channel & rentang tanggal
    ├── BUKA_NOTEPAD_COOKIE.bat          # Buka file input cookies (opsional)
    ├── DOWNLOAD_SEKARANG.bat            # Jalankan downloader channel
    ├── target_channel.txt               # Daftar link channel & filter tanggal
    ├── input_cookie.txt                 # File cookies login
    ├── channel_downloader.py            # Script channel downloader
    └── Hasil_Download/                  # Folder output video (per nama channel)
```

## Prasyarat & Instalasi

- Python 3.10+
- Library yang dibutuhkan:
  ```bash
  pip install -r ../requirements.txt
  ```

## Cara Penggunaan

### Modul 1: Unduh Banyak Link (Video, Shorts, Playlist)
1. Buka `1_Unduh_Banyak_Link/BUKA_NOTEPAD_LINK.bat`.
2. Tempelkan tautan video YouTube (1 baris 1 link), lalu simpan (`Ctrl+S`).
3. *(Opsional untuk video 18+/Restrict)*: Buka `1_Unduh_Banyak_Link/BUKA_NOTEPAD_COOKIE.bat` dan tempelkan cookies.
4. Klik 2x `DOWNLOAD_SEKARANG.bat`.

### Modul 2: Unduh Channel & Rentang Waktu
1. Buka `2_Unduh_Channel_dan_Rentang_Waktu/BUKA_NOTEPAD_TARGET.bat`.
2. Atur tanggal pada `DARI_TANGGAL` dan `SAMPAI_TANGGAL` (format `YYYY-MM-DD`, kosongkan jika ingin mengunduh semua).
3. Tempelkan link channel YouTube (contoh: `https://www.youtube.com/@NamaChannel`).
4. Klik 2x `DOWNLOAD_SEKARANG.bat`. File otomatis dikelompokkan ke dalam subfolder nama channel masing-masing.
