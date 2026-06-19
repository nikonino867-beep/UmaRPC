@echo off
title UmaRPC Startup Watcher
cd /d "C:\PATH\KE\FOLDER_SCRIPT_LU"

echo Starting UmaRPC...
start "UmaRPC" py UmaRPC.py

:LOOP
tasklist /FI "IMAGENAME eq umamusume.exe" | find /I "umamusume.exe" >nul

if %errorlevel%==0 (
    tasklist /V | find /I "screen_detector.py" >nul
    if errorlevel 1 (
        echo Umamusume detected. Starting screen_detector...
        start "screen_detector" py screen_detector.py
    )
) else (
    for /f "tokens=2" %%A in ('wmic process where "commandline like '%%screen_detector.py%%' and name like '%%python%%'" get processid ^| findstr /R "[0-9]"') do (
        echo Umamusume closed. Killing screen_detector PID %%A
        taskkill /PID %%A /T /F >nul 2>&1
    )
)

timeout /t 5 /nobreak >nul
goto LOOP