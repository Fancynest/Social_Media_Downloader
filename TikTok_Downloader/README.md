# TikTok Downloader Suite

Koleksi tool otomatisasi untuk mengunduh video tanpa watermark (No Watermark), slide foto, dan seluruh video profil akun TikTok.

## Struktur Direktori

```text
TikTok_Downloader/
├── 1_Unduh_Banyak_Link/                 # Unduh massal dari daftar link (Video No-Watermark & Slide Foto)
│   ├── BUKA_NOTEPAD_LINK.bat            # Buka file daftar link
│   ├── BUKA_NOTEPAD_COOKIE.bat          # Buka file input cookies (opsional)
│   ├── DOWNLOAD_SEKARANG.bat            # Jalankan downloader
│   ├── link_tiktok.txt                  # Daftar link video/foto TikTok
│   ├── input_cookie.txt                 # File cookies login (opsional)
│   ├── downloader.py                    # Script batch downloader
│   ├── PETUNJUK_PENGGUNAAN.txt          # Panduan lengkap
│   └── Hasil_Download/                  # Folder output video/foto
│
└── 2_Unduh_Profil_dan_Rentang_Waktu/   # Unduh semua konten Akun Profil + Filter Tanggal
    ├── BUKA_NOTEPAD_TARGET.bat          # Buka konfigurasi profil & rentang tanggal
    ├── BUKA_NOTEPAD_COOKIE.bat          # Buka file input cookies (opsional)
    ├── DOWNLOAD_SEKARANG.bat            # Jalankan downloader profil
    ├── target_profil.txt                # Daftar target profil & filter tanggal
    ├── input_cookie.txt                 # File cookies login (opsional)
    ├── profile_downloader.py            # Script profile downloader
    ├── PETUNJUK_PENGGUNAAN.txt          # Panduan lengkap
    └── Hasil_Download/                  # Folder output video (per nama akun @kreator)
```

## Prasyarat & Instalasi

- Python 3.10+
- Library yang dibutuhkan:
  ```bash
  pip install -r ../requirements.txt
  ```

## Cara Penggunaan

### Modul 1: Unduh Banyak Link (Video No-WM & Slide Foto)
1. Buka `1_Unduh_Banyak_Link/BUKA_NOTEPAD_LINK.bat`.
2. Tempelkan tautan video TikTok (1 baris 1 link), lalu simpan (`Ctrl+S`).
   - Mendukung format link panjang (`tiktok.com/@user/video/...`), link pendek (`vt.tiktok.com` / `vm.tiktok.com`), dan postingan slide foto (`photo/...`).
3. *(Opsional untuk video privat/18+)*: Buka `1_Unduh_Banyak_Link/BUKA_NOTEPAD_COOKIE.bat` dan tempelkan cookies.
4. Klik 2x `DOWNLOAD_SEKARANG.bat`. Hasil video otomatis bebas watermark!

### Modul 2: Unduh Profil & Rentang Waktu
1. Buka `2_Unduh_Profil_dan_Rentang_Waktu/BUKA_NOTEPAD_TARGET.bat`.
2. Atur tanggal pada `DARI_TANGGAL` dan `SAMPAI_TANGGAL` (format `YYYY-MM-DD`, kosongkan jika ingin mengunduh semua).
3. Tempelkan username atau tautan profil TikTok (contoh: `https://www.tiktok.com/@nama_akun`, `@nama_akun`, atau `nama_akun`).
4. Klik 2x `DOWNLOAD_SEKARANG.bat`. File otomatis dikelompokkan ke dalam subfolder `@nama_akun` masing-masing.

## Fitur Unggulan
- **No Watermark (HD):** Video diunduh langsung dalam resolusi tertinggi tanpa watermark TikTok.
- **Slide Foto (Photo Mode):** Mendukung pengunduhan rangkaian foto dari postingan slide TikTok.
- **Anti-Duplikat:** Video yang sudah pernah diunduh otomatis dilewati berkat sistem riwayat `download_history.txt`.
- **Dukungan Cookies:** Mendukung unduhan video privat atau konten yang dibatasi usia.
