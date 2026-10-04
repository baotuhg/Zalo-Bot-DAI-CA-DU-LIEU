@echo off
chcp 65001 >nul
title ĐẠI CA DỮ LIỆU - TRUNG TÂM ĐIỀU HÀNH TỰ ĐỘNG
echo ======================================================================
echo    🤖 ĐẠI CA DỮ LIỆU - HỆ THỐNG GIÁM SÁT DỰ ÁN & BOT ZALO TỰ ĐỘNG
echo ======================================================================
echo.

:: 1. Kiểm tra Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ======================================================================
    echo ❌ LỖI: Máy tính chưa cài đặt Python!
    echo 👉 Vui lòng tải Python (từ 3.10 trở lên) tại: https://www.python.org/
    echo    (Khi cài đặt nhớ tích chọn: "Add Python to PATH")
    echo ======================================================================
    echo.
    pause
    exit /b 1
)

:: 2. Tự động khởi tạo .venv nếu chưa có
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Đang tự động thiết lập môi trường ảo Python (.venv)...
    python -m venv .venv
    if not exist ".venv\Scripts\python.exe" (
        echo ❌ Không thể tạo .venv. Vui lòng kiểm tra quyền ghi thư mục!
        pause
        exit /b 1
    )
    echo [1/3] Đang cài đặt các thư viện cần thiết...
    .venv\Scripts\python -m pip install -r requirements.txt --quiet
    echo ✅ Môi trường Python đã sẵn sàng!
    echo.
)

:: 3. Kiểm tra Node.js
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️ CHÚ Ý: Chưa tìm thấy Node.js trên máy!
    echo 👉 Node.js cần thiết để kết nối Zalo cá nhân. Tải tại: https://nodejs.org/
    echo.
)

:: 4. Kiểm tra tài khoản Zalo đã kết nối chưa
if not exist "%USERPROFILE%\.zalo-personal-mcp\credentials.json" (
    echo [2/3] Chưa phát hiện phiên đăng nhập Zalo!
    echo 👉 Đang khởi động màn hình quét mã QR để kết nối...
    echo.
    call 1_KET_NOI_ZALO.bat
)

:: 5. Khởi động Web Control Center & Bot Realtime & Mở trình duyệt
echo.
echo [3/3] Đang khởi động Trung Tâm Điều Hành Web & Bot Realtime...
echo ======================================================================
echo  🌐 Bảng điều hành Local: http://localhost:8080
echo  ☁️  Bảng điều hành Cloud: https://baotuhg.github.io/Zalo-Bot-DAI-CA-DU-LIEU/
echo ======================================================================
echo.
echo 👉 Trình duyệt của bạn sẽ tự động mở trong giây lát.
echo 👉 Cửa sổ này đang duy trì máy chủ điều hành, vui lòng không tắt.
echo.

.venv\Scripts\python web_control.py

pause
