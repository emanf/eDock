@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"

set "RUN_DIR=%~dp0user\run"

if not exist "%RUN_DIR%" (
    exit /b 0
)

for %%f in ("%RUN_DIR%\*.pid") do (
    set "PID="
    set /p PID=<"%%f"
    if not "!PID!"=="" (
        taskkill /PID !PID! /F >nul 2>nul
    )
    del /f /q "%%f" >nul 2>nul
)

exit /b 0
