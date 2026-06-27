@echo off
title Uma RPC - First Time Setup
color 0B

cd /d "%~dp0"

echo ==================================================
echo                 UMA RPC FIRST SETUP
echo ==================================================
echo.
echo Select Language / Pilih Bahasa:
echo [1] English
echo [2] Bahasa Indonesia
echo.
set /p lang="Choose [1-2]: "

if "%lang%"=="1" goto lang_en
if "%lang%"=="2" goto lang_id
goto lang_en

:lang_en
cls
echo ==================================================
echo                 UMA RPC FIRST SETUP
echo ==================================================
echo.
echo DISCLAIMER / IMPORTANT NOTES:
echo.
echo 1. This tool still has some limitations:
echo    - OCR may occasionally retry while UI elements are fading in.
echo    - Does not work in Portrait mode.
echo.
echo 2. You MUST install the Hachimi mod first.
echo    Without Hachimi / matching localized data, some features
echo    might not work as expected.
echo.
echo 3. Umamusume MUST be set to Landscape mode in game settings.
echo    If set to Portrait, the Detector will not work.
echo.
echo 4. Make sure Discord is open before running UmaRPC.py.
echo.
echo 5. This script only installs Python dependencies.
echo    It does NOT install Hachimi and does NOT change game settings.
echo.
echo ==================================================
echo.
pause
goto check_python

:lang_id
cls
echo ==================================================
echo                 UMA RPC FIRST SETUP
echo ==================================================
echo.
echo DISCLAIMER / CATATAN PENTING:
echo.
echo 1. Tool ini masih punya beberapa kekurangan:
echo    - OCR terkadang akan mengulang pembacaan saat elemen UI masih fade/transparan.
echo    - Tidak berfungsi di mode portrait.
echo.
echo 2. Wajib install mod Hachimi dulu.
echo    Tanpa Hachimi / localized data yang sesuai, beberapa fitur
echo    bisa nggak jalan seperti yang diharapkan.
echo.
echo 3. Umamusume WAJIB pakai mode Landscape di pengaturan game.
echo    Kalau Portrait, Detektor tidak akan bekerja.
echo.
echo 4. Pastikan Discord sudah dibuka sebelum menjalankan UmaRPC.py.
echo.
echo 5. Script ini hanya install dependency Python.
echo    Script ini TIDAK menginstall Hachimi dan TIDAK mengubah setting game.
echo.
echo ==================================================
echo.
pause
goto check_python

:check_python
echo.
cls
if "%lang%"=="1" (echo Checking Python...) else (echo Mengecek Python...)
py --version >nul 2>&1
if errorlevel 1 (
    if "%lang%"=="1" (
        echo [ERROR] Python launcher "py" not found.
        echo Please install Python from python.org and check "Add Python to PATH".
    ) else (
        echo [ERROR] Python launcher "py" tidak ditemukan.
        echo Install Python dulu dari python.org, lalu centang "Add Python to PATH".
    )
    echo.
    pause
    exit /b 1
)

if "%lang%"=="1" (echo Python detected:) else (echo Python terdeteksi:)
py --version

echo.
if "%lang%"=="1" (echo Upgrading pip...) else (echo Mengupgrade pip...)
py -m pip install --upgrade pip

echo.
if "%lang%"=="1" (echo Installing dependencies...) else (echo Menginstall dependencies...)
py -m pip install ^
psutil ^
keyboard ^
customtkinter ^
pystray ^
pillow ^
rapidfuzz ^
pypresence ^
rapidocr-onnxruntime ^
opencv-python ^
windows-capture ^
numpy

echo.
cls
echo ==================================================
if "%lang%"=="1" (
    echo Setup complete.
    echo.
    echo How to run:
    echo py UmaRPC.py
    echo.
    echo If you encounter 'module not found' errors, run this setup file again.
) else (
    echo Setup selesai.
    echo.
    echo Cara jalanin:
    echo py UmaRPC.py
    echo.
    echo Kalau ada error module not found, jalanin file setup ini lagi.
)
echo ==================================================
echo.
pause