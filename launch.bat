@echo off
SETLOCAL EnableDelayedExpansion
TITLE Trade Sentinel OS -- Automated Installer & Launcher

echo ===================================================================
echo               TRADE SENTINEL OS -- WINDOWS LAUNCHER
echo ===================================================================
echo.

:: Check for Administrative Privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Administrative privileges required. Elevating prompt...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

CD /D "%~dp0"

:: Execute PowerShell Master Installer and Launcher
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_and_run.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [X] Launch failed with error code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)

pause
