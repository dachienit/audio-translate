@echo off
title Meeting Translator
echo ============================================
echo   Meeting Translator - Setup and Launch
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

:: Install dependencies
echo [1/2] Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [WARNING] Some packages may have failed to install.
    echo Trying again with --user flag...
    pip install -r requirements.txt --quiet --user
)

echo.
echo [2/2] Starting Meeting Translator server...
echo.
echo ============================================
echo   Open http://localhost:3000 in your browser
echo ============================================
echo.

python server.py

pause
