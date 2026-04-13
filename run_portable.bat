@echo off
title Portable Meeting Translator Launcher
echo =======================================================
echo   Meeting Translator - Portable Mode (No Admin / No PATH)
echo =======================================================
echo.

set PYTHON_DIR=%~dp0.python
set PYTHON_EXE=%PYTHON_DIR%\python.exe
set PIP_SCRIPT=%PYTHON_DIR%\get-pip.py

:: 1. Check if local Python exists
if not exist "%PYTHON_EXE%" (
    echo [*] Checking local environment... Portable Python not found.
    echo [*] Downloading Python 3.11 Embeddable x64...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile 'python_embed.zip'"
    
    echo [*] Extracting Python to local folder (.python)...
    powershell -Command "Expand-Archive -Path 'python_embed.zip' -DestinationPath '%PYTHON_DIR%' -Force"
    del python_embed.zip

    echo [*] Configuring Python to support PIP...
    powershell -Command "(Get-Content '%PYTHON_DIR%\python311._pth').replace('#import site', 'import site') | Set-Content '%PYTHON_DIR%\python311._pth'"

    echo [*] Downloading get-pip.py...
    powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PIP_SCRIPT%'"

    echo [*] Installing PIP locally...
    "%PYTHON_EXE%" "%PIP_SCRIPT%"
    
    echo [*] Portable Python setup complete!
    echo.
)

:: 2. Install/Check dependencies using local python
echo [*] Installing/Updating dependencies from requirements.txt...
"%PYTHON_EXE%" -m pip install -r requirements.txt --quiet --disable-pip-version-check

:: 3. Run the server
echo.
echo ============================================
echo   Starting server with Portable Python...
echo   Open http://localhost:3000 in your browser
echo ============================================
echo.

"%PYTHON_EXE%" server.py

pause
