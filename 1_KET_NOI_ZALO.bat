@echo off
chcp 65001 >nul
title 1. Ket noi Zalo Daemon
echo ======================================================================
echo         [BƯỚC 1] KẾT NỐI ZALO MCP DAEMON (CỔNG 3712)
echo ======================================================================
echo.
if exist "%USERPROFILE%\.zalo-personal-mcp\connect.ps1" (
    powershell -ExecutionPolicy Bypass -File "%USERPROFILE%\.zalo-personal-mcp\connect.ps1"
) else (
    echo [Hệ thống] Đang tải và kích hoạt Zalo MCP Daemon...
    call npx -y zalo-personal-mcp login
    call npx -y zalo-personal-mcp daemon start
)
pause
