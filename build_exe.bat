@echo off
title Build Standalone Executable
cd /d "%~dp0"

echo Installing PyInstaller if missing...
pip install pyinstaller

echo.
echo Packaging C69HD Customizer into a standalone executable...
pyinstaller --noconfirm --onedir --windowed ^
    --name "C69HD_Customizer" ^
    --add-data "assets;assets" ^
    --add-data "core;core" ^
    --add-data "gui;gui" ^
    run_gui.py

echo.
echo Build complete! Executable is located in dist\C69HD_Customizer\C69HD_Customizer.exe
pause
