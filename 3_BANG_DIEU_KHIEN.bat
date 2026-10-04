@echo off
chcp 65001 >nul
title 3. Bang Dieu Khien - Dai Ca Du Lieu
cd /d "%~dp0"
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0app_control_center.py"
