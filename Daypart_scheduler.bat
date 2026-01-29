@echo off
title AkiraTV Daypart Scheduler
color 0A

:: Get the directory where this batch file is located
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo ========================================
echo    AkiraTV Daypart Scheduler Launcher
echo ========================================
echo.
echo Current Directory: %CD%
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in PATH!
    echo.
    echo Please install Python or add it to your PATH environment variable.
    echo You can download Python from: https://www.python.org/downloads/
    echo.
    echo If Python is installed elsewhere, you may need to edit this batch file
    echo to use the full path to your python.exe
    echo.
    pause
    exit /b 1
)

:: Show Python version
echo [INFO] Found Python:
python --version
echo.

:: Check if the daypart scheduler script exists
if not exist "daypart_scheduler.py" (
    echo [ERROR] daypart_scheduler.py not found in current directory!
    echo.
    echo Please make sure daypart_scheduler.py is in the same directory as this batch file.
    echo.
    pause
    exit /b 1
)

:: Check if config.json exists
if not exist "config.json" (
    echo [WARNING] config.json not found in current directory!
    echo The scheduler will use default settings.
    echo.
)

:: Check if collections file exists
if not exist "collections.json" (
    if not exist "collections_akiratv.json" (
        echo [WARNING] No collections file found!
        echo Expected: collections.json or collections_akiratv.json
        echo.
    )
)

echo [INFO] Starting Daypart Scheduler...
echo.

:: Run the daypart scheduler
python daypart_scheduler.py

:: Check if the script ran successfully
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Daypart scheduler exited with error code %errorlevel%
    echo.
    pause
) else (
    echo.
    echo [INFO] Daypart scheduler closed successfully.
)

:: Optional: Keep window open for a moment to read any messages
timeout /t 2 /nobreak >nul