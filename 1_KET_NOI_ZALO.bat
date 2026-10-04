@echo off
chcp 65001 >nul
title Ket noi Zalo MCP Daemon
echo =======================================================
echo         KẾT NỐI ZALO MCP DAEMON (CỔNG 3712)
echo =======================================================
powershell -ExecutionPolicy Bypass -File "C:\Users\baotu\.zalo-personal-mcp\connect.ps1"
pause
