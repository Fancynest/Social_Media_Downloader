@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHON_BIN=C:\laragon\bin\python\python-3.13\python.exe
if not exist "%PYTHON_BIN%" set PYTHON_BIN=python
echo ===================================================
echo   LOGIN INSTAGRAM SECARA INTERAKTIF (INSTALOADER)
echo ===================================================
echo Masukkan username dan password Anda jika diminta.
echo Sesi login akan disimpan secara aman di 'session.dat'.
echo.
"%PYTHON_BIN%" -c "import instaloader; L = instaloader.Instaloader(); u = input('Masukkan username IG: ').strip(); L.interactive_login(u); L.save_session_to_file('session.dat'); open('session_user.txt', 'w', encoding='utf-8').write(u)"
echo.
pause
