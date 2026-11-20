@echo off
title Build Standalone Executable
cd /d "%~dp0"

echo Installing PyInstaller if missing...
pip install pyinstaller

echo.
echo Packaging Onyx Boox C69HD Power Studio into a standalone executable...
python -m PyInstaller --noconfirm --onedir --windowed ^
    --name "Onyx_C69HD_Power_Studio" ^
    --add-data "assets;assets" ^
    --add-data "scripts;scripts" ^
    --add-data "core;core" ^
    --add-data "gui;gui" ^
    --collect-all customtkinter ^
    --collect-all PIL ^
    run_gui.py

echo.
echo Build complete! Executable is located in dist\Onyx_C69HD_Power_Studio\Onyx_C69HD_Power_Studio.exe
pause
