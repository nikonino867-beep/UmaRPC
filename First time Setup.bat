@echo off
title Uma RPC - First Time Setup
color 0B

cd /d "%~dp0"

echo ==================================================
echo                 UMA RPC FIRST SETUP
echo ==================================================
echo.
echo DISCLAIMER / CATATAN PENTING:
echo.
echo 1. Tool ini masih punya beberapa kekurangan:
echo    - Bisa spike CPU sesekali saat OCR / detector jalan.
echo    - Tidak berfungsi di mode potrait
echo.
echo 2. Wajib install mod Hachimi dulu.
echo    Tanpa Hachimi / localized data yang sesuai, beberapa fitur
echo    bisa nggak jalan seperti yang diharapkan.
echo.
echo 3. Umamusume WAJIB pakai mode Landscape di pengaturan game.
echo    Kalau Portrait / layout beda, crop detector bisa salah.
echo.
echo 4. Pastikan Discord sudah dibuka sebelum menjalankan UmaRPC.py.
echo.
echo 5. Script ini hanya install dependency Python.
echo    Script ini TIDAK menginstall Hachimi dan TIDAK mengubah setting game.
echo.
echo ==================================================
echo.
pause
echo.
cls
echo Checking Python...
py --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python launcher "py" tidak ditemukan.
    echo Install Python dulu dari python.org, lalu centang "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo Python detected:
py --version

echo.
echo Upgrading pip...
py -m pip install --upgrade pip

echo.
echo Installing dependencies...
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
mss ^
numpy
echo.
cls
echo ==================================================
echo Setup selesai.
echo.
echo Cara jalanin:
echo py UmaRPC.py
echo.
echo Kalau ada error module not found, jalanin file setup ini lagi.
echo ==================================================
echo.
pause