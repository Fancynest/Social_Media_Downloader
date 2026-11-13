@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "input_cookie.txt" (
    echo # Tempelkan hasil ekspor cookies dari situs thisvid.com di sini ^(jika video butuh login^) > "input_cookie.txt"
    echo # Gunakan ekstensi 'Get cookies.txt LOCALLY' saat membuka tab thisvid.com di browser >> "input_cookie.txt"
)
notepad.exe "input_cookie.txt"
