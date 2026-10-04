@echo off
chcp 65001 >nul
title 1. Ket noi Zalo Daemon
echo ======================================================================
echo         [BƯỚC 1] KẾT NỐI ZALO MCP DAEMON (CỔNG 3712)
echo ======================================================================
echo.

where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ======================================================================
    echo ❌ LỖI: Chưa tìm thấy Node.js trên máy tính của bạn!
    echo 👉 Để kết nối Zalo, vui lòng tải và cài đặt Node.js từ: https://nodejs.org/
    echo    (Chọn bản LTS khuyên dùng, bấm Next cài đặt mặc định là xong)
    echo ======================================================================
    echo.
    pause
    exit /b 1
)

if exist "%USERPROFILE%\.zalo-personal-mcp\connect.ps1" (
    powershell -ExecutionPolicy Bypass -File "%USERPROFILE%\.zalo-personal-mcp\connect.ps1"
) else (
    echo [Hệ thống] Đang tải và kích hoạt Zalo MCP Daemon...
    call npx -y zalo-personal-mcp login
    call npx -y zalo-personal-mcp daemon start
)
pause
