@echo off
chcp 65001 >nul
title Bot Zalo - Dai Ca Du Lieu
echo =======================================================
echo        KHỞI CHẠY BOT ZALO "ĐẠI CA DỮ LIỆU"
echo =======================================================
cd /d "%~dp0"
.venv\Scripts\python.exe run_data_boss.py
pause
