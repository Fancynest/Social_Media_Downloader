@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Setup Social Media Downloader Suite

echo =====================================================================
echo       SETUP OTOMATIS: SOCIAL MEDIA DOWNLOADER SUITE
echo =====================================================================
echo.
echo [*] Memeriksa instalasi Python di sistem Anda...

set "PYTHON_BIN="
if exist "C:\laragon\bin\python\python-3.13\python.exe" (
    set "PYTHON_BIN=C:\laragon\bin\python\python-3.13\python.exe"
)
if "%PYTHON_BIN%"=="" (
    where python >nul 2>nul
    if %errorlevel% equ 0 set "PYTHON_BIN=python"
)
if "%PYTHON_BIN%"=="" (
    where py >nul 2>nul
    if %errorlevel% equ 0 set "PYTHON_BIN=py -3"
)

if "%PYTHON_BIN%"=="" (
    echo [X] Python TIDAK DITEMUKAN!
    echo.
    echo     Silakan unduh dan pasang Python 3.10+ terlebih dahulu di:
    echo     https://www.python.org/downloads/
    echo.
    echo     PENTING: Pastikan Anda MENCENTANG kotak:
    echo     [X] "Add Python to PATH" saat proses instalasi dimulai.
    echo.
    pause
    exit /b 1
)

echo [OK] Python terdeteksi!
"%PYTHON_BIN%" --version

echo.
echo [*] Memasang dan memperbarui seluruh library yang dibutuhkan...
echo     (yt-dlp, instaloader, gallery-dl, requests)
echo.

"%PYTHON_BIN%" -m pip install -r "%~dp0requirements.txt"

echo.
echo [*] Memeriksa FFmpeg...
where ffmpeg >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] FFmpeg terdeteksi dan aktif di sistem.
) else (
    echo [!] Catatan: FFmpeg belum terpasang di PATH sistem.
    echo     Video tetap dapat diunduh langsung, namun untuk resolusi
    echo     2K / 4K YouTube disarankan memasang FFmpeg.
)

echo.
echo =====================================================================
echo [OK] SEMUA PERSIAPAN SELESAI!
echo =====================================================================
echo Anda sekarang bisa langsung membuka folder downloader mana saja:
echo   1. YouTube_Downloader/
echo   2. Instagram_Downloader/
echo   3. Twitter_X_Downloader/
echo   4. TikTok_Downloader/
echo.
echo Lalu klik DOWNLOAD_SEKARANG.bat atau JALANKAN_DOWNLOADER.bat.
echo =====================================================================
echo.
pause