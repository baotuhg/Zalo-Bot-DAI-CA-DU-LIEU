@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title 0. Cai Dat Moi Truong Tu Dong - Dai Ca Du Lieu
cd /d "%~dp0"

echo ======================================================================
echo       🛠️ [BƯỚC 0] CÀI ĐẶT MÔI TRƯỜNG TỰ ĐỘNG - ĐẠI CA DỮ LIỆU
echo ======================================================================
echo.
echo [1/3] Đang kiểm tra Python trên máy tính của bạn...
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
echo.
echo [2/3] Đang tạo môi trường ảo Python (.venv)...
if not exist "%~dp0.venv\Scripts\python.exe" (
    python -m venv "%~dp0.venv"
    echo ✅ Đã tạo thư mục .venv thành công.
) else (
    echo ℹ️ Thư mục .venv đã tồn tại.
)

echo.
echo [3/3] Đang cài đặt các thư viện cần thiết từ requirements.txt...
if exist "%~dp0.venv\Scripts\pip.exe" (
    "%~dp0.venv\Scripts\pip.exe" install --upgrade pip
    "%~dp0.venv\Scripts\pip.exe" install -r "%~dp0requirements.txt"
) else (
    python -m pip install -r "%~dp0requirements.txt"
)

echo.
echo ======================================================================
echo 🎉 CHÚC MỪNG! HỆ THỐNG ĐÃ ĐƯỢC THIẾT LẬP HOÀN TOÀN TỰ ĐỘNG!
echo.
echo Các bước tiếp theo:
echo  👉 Bước 1: Chạy "1_KET_NOI_ZALO.bat" để kết nối tài khoản Zalo.
echo  👉 Bước 2: Chạy "2_CHAY_BOT_REALTIME.bat" để Bot tự động giám sát.
echo  👉 Bước 3: Chạy "3_BANG_DIEU_KHIEN.bat" để xem bảng dữ liệu và xuất Excel.
echo  👉 Bước 4: Chạy "4_XEM_WEB_DASHBOARD.bat" để xem Dashboard trực tuyến.
echo ======================================================================
echo.
pause
