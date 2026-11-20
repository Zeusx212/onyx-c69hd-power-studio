@echo off
title Install Android SDK Platform-Tools (ADB & Fastboot)
cd /d "%~dp0"

echo ====================================================================
echo   Onyx Boox C69HD - Auto-detect and Install ADB & Fastboot
echo ====================================================================
echo.

python install_adb.py %*

echo.
pause
