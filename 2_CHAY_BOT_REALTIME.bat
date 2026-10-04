@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title 2. Bot Zalo Realtime - Dai Ca Du Lieu
cd /d "%~dp0"

:: Kiểm tra môi trường Python (.venv)
if exist "%~dp0.venv\Scripts\python.exe" goto RUN

echo ======================================================================
echo  [LẦN ĐẦU KHỞI CHẠY] TỰ ĐỘNG THIẾT LẬP MÔI TRƯỜNG CHO DỰ ÁN
echo ======================================================================
echo.
echo Đang kiểm tra Python trên máy tính của bạn...

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ======================================================================
    echo ❌ LỖI: Máy tính chưa cài đặt Python hoặc chưa tick "Add Python to PATH"!
    echo 👉 Vui lòng tải Python từ: https://www.python.org/downloads/
    echo ⚠️ Khi cài đặt, hãy tích chọn ô: [x] Add python.exe to PATH
    echo ======================================================================
    echo.
    pause
    exit /b 1
)

echo ✅ Đã tìm thấy Python hệ thống.
echo ⏳ Đang tự động tạo môi trường ảo (.venv)...
python -m venv "%~dp0.venv"

if not exist "%~dp0.venv\Scripts\python.exe" (
    echo ⚠️ Không tạo được .venv, đang cài thư viện trực tiếp...
    python -m pip install -r "%~dp0requirements.txt"
    set "PY_CMD=python"
    goto EXEC
)

echo ⏳ Đang tự động cài đặt các thư viện cần thiết (requirements.txt)...
"%~dp0.venv\Scripts\pip.exe" install -r "%~dp0requirements.txt"
echo.
echo ✅ THIẾT LẬP MÔI TRƯỜNG THÀNH CÔNG!
echo ======================================================================
echo.

:RUN
set "PY_CMD=%~dp0.venv\Scripts\python.exe"

:EXEC
echo ======================================================================
echo         [BƯỚC 2] BOT ZALO REALTIME TỰ HÀNH 100%%
echo      (Tự động bóc tách báo cáo từ các nhóm Zalo công trường)
echo ======================================================================
echo.
"%PY_CMD%" -u run_data_boss.py
pause
