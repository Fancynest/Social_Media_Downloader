@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHON_BIN=C:\laragon\bin\python\python-3.13\python.exe
if not exist "%PYTHON_BIN%" set PYTHON_BIN=python
"%PYTHON_BIN%" ig_filter_downloader.py
