@echo off
cd /d "%~dp0"
if not exist "input_cookie.txt" type nul > "input_cookie.txt"
start notepad.exe "input_cookie.txt"
