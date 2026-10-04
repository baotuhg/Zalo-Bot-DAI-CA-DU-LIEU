@echo off
chcp 65001 >nul
title Thu nghiem Bot Dai Ca Du Lieu
cd /d "%~dp0"
.venv\Scripts\python.exe cli_data_boss.py
pause
