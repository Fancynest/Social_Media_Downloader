@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "input_cookie.txt" (
    echo # Tempelkan hasil ekspor cookies dari situs x.com / twitter.com di sini > "input_cookie.txt"
    echo # Gunakan ekstensi 'Get cookies.txt LOCALLY' saat membuka tab x.com >> "input_cookie.txt"
)
notepad.exe "input_cookie.txt"
