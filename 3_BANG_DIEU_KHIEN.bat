@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title 3. Bang Dieu Khien - Dai Ca Du Lieu
cd /d "%~dp0"

:: Kiểm tra nếu .venv đã có pythonw.exe thì chạy ngay lập tức
if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0app_control_center.py"
    exit /b 0
)

:: Nếu chưa có .venv, tiến hành thiết lập tự động
echo ======================================================================
echo  [LẦN ĐẦU KHỞI CHẠY] TỰ ĐỘNG THIẾT LẬP MÔI TRƯỜNG CHO BẢNG ĐIỀU KHIỂN
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

if not exist "%~dp0.venv\Scripts\pythonw.exe" (
    echo ⚠️ Không tạo được .venv, đang cài thư viện trực tiếp...
    python -m pip install -r "%~dp0requirements.txt"
    start "" pythonw "%~dp0app_control_center.py"
    exit /b 0
)

echo ⏳ Đang tự động cài đặt các thư viện cần thiết (requirements.txt)...
"%~dp0.venv\Scripts\pip.exe" install -r "%~dp0requirements.txt"
echo.
echo ✅ THIẾT LẬP MÔI TRƯỜNG THÀNH CÔNG!
echo Đang mở Bảng điều khiển...
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0app_control_center.py"
exit /b 0
