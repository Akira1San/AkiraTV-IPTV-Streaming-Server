@echo off
REM AkiraTV Web Interface Launcher
REM This batch file starts the web UI for AkiraTV

echo ================================================
echo    AkiraTV Web Interface Launcher
echo ================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH!
    echo.
    echo Please install Python from https://www.python.org/
    echo.
    pause
    exit /b 1
)

REM Check if launch_web.py exists
if not exist "launch_web.py" (
    echo ERROR: launch_web.py not found!
    echo.
    echo Make sure you're running this from the project root directory.
    echo.
    pause
    exit /b 1
)

REM Start the web interface
echo Starting AkiraTV Web Interface...
echo.
python launch_web.py

REM If Python exits with error, pause so user can see the error
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to start web interface!
    echo.
    pause
)
