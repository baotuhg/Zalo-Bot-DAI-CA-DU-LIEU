@echo off
chcp 65001 >nul
title 1. Ket noi Zalo Daemon
echo ======================================================================
echo         [BƯỚC 1] KẾT NỐI ZALO MCP DAEMON (CỔNG 3712)
echo ======================================================================
echo.
powershell -ExecutionPolicy Bypass -File "C:\Users\baotu\.zalo-personal-mcp\connect.ps1"
pause
