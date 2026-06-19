@echo off
title MATAY AI Server
echo ==============================================
echo MATAY AI Server Startup
echo ==============================================

:: Check if virtual environment exists
IF NOT EXIST ".venv" (
    echo [1/3] Creating new Virtual Environment...
    python -m venv .venv
) ELSE (
    echo [1/3] Virtual Environment found.
)

:: Activate the virtual environment
echo [2/3] Activating Virtual Environment...
call .venv\Scripts\activate.bat

:: Check if libraries are installed (by checking if torch exists)
echo [3/3] Checking if libraries are installed...
python -c "import torch" >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Libraries are missing. Downloading and installing them now...
    echo Please wait, this might take a few minutes...
    pip install -r requirements.txt
    echo Installation complete!
) ELSE (
    echo All libraries are already installed! Skipping download.
)

echo.
echo ==============================================
echo Starting the Server...
echo ==============================================
python server.py

pause
