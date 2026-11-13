@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "input_cookie.txt" (
    echo # Tempelkan cookies YouTube di sini (hasil copas ekstensi atau raw cookie string) > "input_cookie.txt"
    echo # Simpan file ini (Ctrl + S), lalu tutup Notepad. >> "input_cookie.txt"
)
notepad.exe "input_cookie.txt"
