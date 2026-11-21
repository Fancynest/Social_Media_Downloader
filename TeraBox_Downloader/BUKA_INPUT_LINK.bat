@echo off
cd /d "%~dp0"
if not exist "input_links.txt" type nul > "input_links.txt"
start notepad.exe "input_links.txt"
