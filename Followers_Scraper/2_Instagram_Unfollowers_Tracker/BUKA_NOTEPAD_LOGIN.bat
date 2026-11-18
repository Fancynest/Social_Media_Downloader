@echo off
cd /d "%~dp0"
if not exist "input_cookie.txt" (
    echo # ============================================================================== > "input_cookie.txt"
    echo # TEMPELKAN (PASTE) TEKS COOKIES DARI EKSTENSI BROWSER DI SINI >> "input_cookie.txt"
    echo # ============================================================================== >> "input_cookie.txt"
    echo # Petunjuk Penggunaan: >> "input_cookie.txt"
    echo # 1. Buka instagram.com di Chrome / Edge (pastikan sudah login). >> "input_cookie.txt"
    echo # 2. Klik ekstensi 'Get cookies.txt LOCALLY' di pojok kanan atas browser. >> "input_cookie.txt"
    echo # 3. Klik tombol 'Export' atau salin seluruh teks cookies yang muncul. >> "input_cookie.txt"
    echo # 4. Tempelkan (paste) seluruh teks tersebut di file Notepad ini. >> "input_cookie.txt"
    echo # 5. Simpan file ini (tekan CTRL + S), lalu tutup Notepad. >> "input_cookie.txt"
    echo # 6. Klik 2x file "LOGIN_AKUN.bat" untuk memverifikasi dan mengaktifkan sesi login! >> "input_cookie.txt"
    echo # ============================================================================== >> "input_cookie.txt"
)
start notepad.exe "input_cookie.txt"
