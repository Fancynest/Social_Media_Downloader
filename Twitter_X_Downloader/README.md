# Twitter / X Downloader Suite

Koleksi tool otomatisasi untuk mengunduh foto kualitas asli dan video kualitas tertinggi dari Twitter / X.

## Struktur Direktori

```text
Twitter_X_Downloader/
├── 1_Unduh_Banyak_Link/                 # Unduh massal foto & video dari daftar tautan postingan
│   ├── BUKA_NOTEPAD_LINK.bat            # Buka file daftar tautan
│   ├── BUKA_NOTEPAD_COOKIE.bat          # Buka file cookies login (opsional)
│   ├── DOWNLOAD_SEKARANG.bat            # Jalankan downloader postingan
│   ├── link_video.txt                   # Daftar link postingan X/Twitter
│   ├── input_cookie.txt                 # File cookies login
│   ├── downloader.py                    # Script batch downloader
│   └── Hasil_Download/                  # Folder output foto & video
│
└── 2_Unduh_Profil_dan_Rentang_Waktu/   # Unduh semua media dari profil akun + filter rentang tanggal
    ├── BUKA_NOTEPAD_TARGET.bat          # Buka konfigurasi profil & filter tanggal
    ├── BUKA_NOTEPAD_COOKIE.bat          # Buka file cookies login (opsional)
    ├── DOWNLOAD_SEKARANG.bat            # Jalankan downloader profil
    ├── target_profil.txt                # Daftar link profil & filter tanggal
    ├── input_cookie.txt                 # File cookies login
    ├── profile_downloader.py            # Script profil downloader
    └── Hasil_Download/                  # Folder output media (per akun profil)
```

## Prasyarat & Instalasi

- Python 3.10+
- Library yang dibutuhkan:
  ```bash
  pip install -r ../requirements.txt
  ```

## Cara Penggunaan

### Modul 1: Unduh Banyak Link (Postingan Satuan / Massal)
1. Buka `1_Unduh_Banyak_Link/BUKA_NOTEPAD_LINK.bat`.
2. Tempelkan tautan postingan X/Twitter (1 baris 1 link), lalu simpan (`Ctrl+S`).
3. *(Opsional untuk postingan 18+/Protected)*: Buka `1_Unduh_Banyak_Link/BUKA_NOTEPAD_COOKIE.bat` dan tempelkan cookies.
4. Klik 2x `DOWNLOAD_SEKARANG.bat`.

### Modul 2: Unduh Profil & Rentang Waktu
1. Buka `2_Unduh_Profil_dan_Rentang_Waktu/BUKA_NOTEPAD_TARGET.bat`.
2. Atur tanggal pada `DARI_TANGGAL` dan `SAMPAI_TANGGAL` (format `YYYY-MM-DD`, kosongkan jika ingin mengunduh semua media).
3. Tempelkan link profil pengguna (contoh: `https://x.com/username` atau `@username`).
4. Klik 2x `DOWNLOAD_SEKARANG.bat`. File otomatis tersimpan di folder `Hasil_Download/[username]/`.
