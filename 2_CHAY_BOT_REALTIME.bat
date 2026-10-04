@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title 2. Bot Zalo Realtime - Dai Ca Du Lieu
echo ======================================================================
echo         [BƯỚC 2] BOT ZALO REALTIME TỰ HÀNH 100%%
echo      (Tự động bóc tách báo cáo từ các nhóm Zalo công trường)
echo ======================================================================
echo.
cd /d "%~dp0"
.venv\Scripts\python.exe -u run_data_boss.py
pause
