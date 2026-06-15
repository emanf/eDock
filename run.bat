@echo off
setlocal

cd /d "%~dp0"

set "RUN_DIR=%~dp0user\run"
if not exist "%RUN_DIR%" mkdir "%RUN_DIR%"

where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 (
        msg * "Python is not installed. Please install Python first."
        exit /b 1
    ) else (
        set "PY_CMD=py"
    )
) else (
    set "PY_CMD=python"
)

where pythonw >nul 2>nul
if errorlevel 1 (
    set "PYW_CMD=%PY_CMD%"
) else (
    set "PYW_CMD=pythonw"
)

if not exist "requirements.txt" (
    msg * "requirements.txt not found."
    exit /b 1
)

%PY_CMD% -m pip --version >nul 2>nul
if errorlevel 1 (
    msg * "pip is not installed."
    exit /b 1
)

%PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    msg * "Failed to install requirements."
    exit /b 1
)

set "TARGET=%~dp0main.py"
if exist "%~dp0main.pyw" set "TARGET=%~dp0main.pyw"

powershell -WindowStyle Hidden -Command ^
    "$p = Start-Process -FilePath '%PYW_CMD%' -ArgumentList '\"%TARGET%\"' -PassThru; " ^
    "$p.Id | Out-File -FilePath '%RUN_DIR%\%COMPUTERNAME%_%RANDOM%_%RANDOM%.pid' -Encoding ascii"

exit /b 0
