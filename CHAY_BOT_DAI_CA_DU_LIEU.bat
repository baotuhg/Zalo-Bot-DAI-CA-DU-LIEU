@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title Bot Zalo - Dai Ca Du Lieu
echo ======================================================================
echo          🤖 BOT ZALO "ĐẠI CA DỮ LIỆU" - DỰ ÁN CÔNG TRƯỜNG
echo ======================================================================
echo.
cd /d "%~dp0"
.venv\Scripts\python.exe -u run_data_boss.py
pause
