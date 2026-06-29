@echo off
setlocal

if "%~1"=="" (
    set "root_dir=%cd%"
) else (
    set "root_dir=%~1"
)
echo Cleaning __pycache__ directories under "%root_dir%"

for /f "delims=" %%D in ('dir /ad /s /b "%root_dir%\__pycache__" 2^>nul') do (
    echo Removing "%%D"
    rd /s /q "%%D"
)
echo Done.
endlocal
