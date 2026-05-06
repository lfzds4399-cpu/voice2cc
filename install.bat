@echo off
chcp 65001 >nul
cd /d %~dp0
title voice2ai - install
echo voice2ai · install dependencies
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [error] Python not found in PATH.
    echo Install Python 3.10+ from https://www.python.org/downloads/ and check "Add to PATH".
    pause
    exit /b 1
)

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [warn] pip install failed. Common causes on Windows:
    echo   - sounddevice needs the Microsoft Visual C++ Redistributable
    echo     ^(grab it from https://aka.ms/vs/17/release/vc_redist.x64.exe^)
    echo   - corporate proxy / GFW blocking PyPI — try a mirror:
    echo     python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
    pause
    exit /b 2
)

echo.
echo ============================================
echo Done. Run start.bat to launch voice2ai.
echo ============================================
pause
