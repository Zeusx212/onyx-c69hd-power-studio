@echo off
title Onyx Boox C69HD Customizer
cd /d "%~dp0"

where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python was not found in your PATH. Please install Python 3.8+.
    pause
    exit /b 1
)

python run_gui.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with code %ERRORLEVEL%.
    pause
)
