@echo off
title A.E.G.I.S. Core Initialization
color 0B
mode con: cols=85 lines=30

echo.
echo    ======================================================================
echo.
echo           db      d88888b  d888b  d888888b .d8888.      .o88b.  .d88b.  d8888b. d88888b 
echo          d88b     88'     88' Y8b   `88'   88'  YP     d8P  Y8 .8P  Y8. 88  `8D 88'     
echo         d8'`8b    88ooooo 88        88    `8bo.       8P      88    88 88oobY' 88ooooo 
echo        d8Y  Y8b   88~~~~~ 88  ooo   88      `Y8b.     8b      88    88 88`8b   88~~~~~ 
echo       d8P    Y8b  88.     88. ~8~  .88.   db   8D     Y8b  d8 `8b  d8' 88 `88. 88.     
echo      d8P      Y8b Y88888P  Y888P Y888888P `8888Y'      `Y88P'  `Y88P'  88   YD Y88888P 
echo.
echo    ======================================================================
echo.
echo    [SYSTEM] Initiating Power Protocols...
timeout /t 1 /nobreak >nul

echo    [SYSTEM] Bypassing College Mainframe...
timeout /t 1 /nobreak >nul

echo    [SYSTEM] Establishing connection to ThingWorx Neural Net...
timeout /t 1 /nobreak >nul

echo    [SYSTEM] Calibrating ESP32 Sensor Arrays...
timeout /t 1 /nobreak >nul

echo.
echo    [A.E.G.I.S.] All systems nominal. Starting Python Core...
echo.

:: Start the Flask server in the background and wait 3 seconds
start /b python app.py
timeout /t 3 /nobreak >nul

:: Open the browser to the dashboard
echo    [A.E.G.I.S.] Opening Visual Interface...
start http://localhost:5000

echo.
echo    [A.E.G.I.S.] Server is running. Press any key to shutdown A.E.G.I.S...
pause >nul

:: When user presses a key, kill the python server
echo.
echo    [SYSTEM] Shutting down A.E.G.I.S. Core...
taskkill /F /IM python.exe /T >nul 2>&1
echo    [SYSTEM] Offline.
timeout /t 2 /nobreak >nul
exit
