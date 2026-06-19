@echo off
title MATAY AI Frontend
echo ==============================================
echo MATAY AI User Interface Startup
echo ==============================================

cd matay-ui

IF NOT EXIST "node_modules" (
    echo [1/2] Installing UI Dependencies...
    echo Please wait, this might take a minute...
    call npm install
) ELSE (
    echo [1/2] UI Dependencies found.
)

echo.
echo [2/2] Starting the User Interface...
echo ==============================================
call npm run dev

pause
