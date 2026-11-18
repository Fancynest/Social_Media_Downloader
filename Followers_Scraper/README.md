# 👥 Social Media Followers Scraper Suite

Folder ini khusus dirancang untuk melakukan *scraping* dan mengekstrak daftar **Followers (Pengikut)** serta **Following (Yang Diikuti)** dari berbagai platform media sosial ke dalam format file **.TXT** (daftar username bersih) dan **.CSV** (tabel spreadsheet Excel lengkap).

---

## 📂 Struktur Modul

```text
Followers_Scraper/
├── 1_Instagram_Followers/             # Scraper Followers & Following Instagram
│   ├── BUKA_INPUT_TARGET.bat         # Shortcut cepat buka target di Notepad
│   ├── BUKA_NOTEPAD_LOGIN.bat        # Shortcut paste cookies login di Notepad
│   ├── LOGIN_AKUN.bat                # Verifikasi & simpan sesi login akun
│   ├── JALANKAN_SCRAPER.bat          # Jalankan proses scraping
│   ├── PETUNJUK_PENGGUNAAN.txt       # Panduan lengkap penggunaan
│   ├── input_target.txt              # File daftar target & konfigurasi scraper
│   ├── input_cookie.txt              # File input cookies
│   ├── ig_follower_scraper.py        # Script utama scraper Instagram
│   └── Hasil_Scrape/                 # Folder penyimpanan hasil file .txt & .csv
│
├── 2_Instagram_Unfollowers_Tracker/   # Deteksi Unfollower & Yang Tidak Follow Back
│   ├── BUKA_NOTEPAD_LOGIN.bat        # Shortcut paste cookies login di Notepad
│   ├── LOGIN_AKUN.bat                # Verifikasi & simpan sesi login akun
│   ├── CEK_UNFOLLOWERS.bat           # Jalankan analisis perbandingan akun
│   ├── PETUNJUK_PENGGUNAAN.txt       # Panduan lengkap fitur unfollowers
│   ├── ig_unfollowers_tracker.py     # Script analitik unfollowers & mutual
│   └── Hasil_Analisis/               # Folder hasil analisis (CSV Excel & TXT)
│
└── README.md                         # Dokumentasi modul scraper
```

---

## 📸 1. Instagram Followers & Following Scraper

### Fitur Utama:
1. **Dua Format Penyimpanan Sekaligus**:
   - **File `.txt`**: Menyimpan daftar username baris demi baris, siap digunakan untuk tools lain, automasi, atau mass mention.
   - **File `.csv`**: Format spreadsheet Excel (UTF-8 BOM) lengkap dengan metadata: *Nomor, Username, Nama Lengkap, User ID, Centang Biru, Status Akun Privat, Link URL Profil, dan Link Foto Profil*.
2. **Sinkronisasi Sesi Login Otomatis**:
   - Jika Anda sudah pernah login di folder `Instagram_Downloader/`, scraper ini akan **langsung otomatis terhubung** ke sesi akun tersebut tanpa perlu login ulang!
   - Mendukung login aman via Cookies (Get cookies.txt LOCALLY) maupun kredensial Username & Password (+ 2FA).
3. **Penyaringan Fleksibel**:
   - Dukungan mengambil data `followers` (pengikut) atau `following` (yang diikuti).
   - Dukungan pengaturan limit jumlah data (`MAKSIMAL_DATA=100`, atau `0` untuk mengambil semua).
4. **Proteksi Keamanan Akun (Anti-Banned)**:
   - Jeda acak (*sleep jitter*) antar request.
   - Jeda pendinginan berkala setiap 50 follower.
   - Auto-pause 45 detik jika Instagram memberikan peringatan *rate limit* sementara.
   - Tombol penghenti darurat (`Ctrl + C`) yang tetap **menyimpan seluruh data yang sudah didapatkan** sebelum program ditutup.

---

## 🚀 Panduan Cara Pakai Cepat

1. **Persiapan Akun (Login)**:
   - Buka `BUKA_NOTEPAD_LOGIN.bat`, paste cookies dari ekstensi browser Anda, lalu simpan (`Ctrl + S`).
   - Klik 2x `LOGIN_AKUN.bat` untuk memverifikasi akun Anda.
   *(Jika sudah pernah login di Instagram Downloader, langkah ini bisa langsung dilewati).*
2. **Tentukan Target Akun**:
   - Klik 2x `BUKA_INPUT_TARGET.bat`.
   - Masukkan username atau link URL akun target (contoh: `cristiano` atau `https://www.instagram.com/cristiano/`).
   - Simpan (`Ctrl + S`) dan tutup Notepad.
3. **Mulai Scraping**:
   - Klik 2x `JALANKAN_SCRAPER.bat`.
   - File hasil akan otomatis tersimpan rapi di dalam folder `Hasil_Scrape/`.

---

## 🕵️ 2. Instagram Unfollowers & Follback Tracker

Modul ini menjawab pertanyaan paling dicari pengguna media sosial: *"Siapa saja yang diam-diam unfollow saya atau tidak mem-follow back akun saya?"*

### Fitur Analisis:
1. **Tidak Follow Balik (Unfollowers / Not Following Back)**:
   - Menemukan seluruh akun yang Anda follow (Following), tapi mereka **TIDAK follow balik** akun Anda.
2. **Fans (Tidak Anda Follow Balik)**:
   - Menemukan akun-akun yang mem-follow Anda, namun belum sempat Anda follow balik.
3. **Mutual (Saling Follow)**:
   - Daftar teman dan akun yang saling mem-follow satu sama lain.
4. **Riwayat Unfollow Sejak Scan Terakhir**:
   - Tool ini otomatis menyimpan snapshot database riwayat (`riwayat_followers.json`).
   - Saat Anda menjalankan tool ini di hari-hari berikutnya, script akan langsung memunculkan **daftar akun yang hilang/unfollow Anda sejak pengecekan terakhir**!

### Cara Menggunakan Unfollowers Tracker:
1. Masuk ke folder `Followers_Scraper/2_Instagram_Unfollowers_Tracker/`.
2. Klik 2x file `CEK_UNFOLLOWERS.bat`.
3. Tunggu proses pembacaan selesai, papan skor ringkasan akan langsung muncul di layar dan file detail tersimpan rapi di folder `Hasil_Analisis/`.

