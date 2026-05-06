@echo off
chcp 65001 >nul
cd /d %~dp0..

title voice2ai - build exe
echo voice2ai · PyInstaller build (folder mode)
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [error] Python not found.
    pause & exit /b 1
)

python -m pip install --upgrade pip pyinstaller >nul

if not exist dist mkdir dist
python -m PyInstaller build_tools\voice2ai.spec --clean --noconfirm
if errorlevel 1 (
    echo [error] PyInstaller build failed. See output above.
    pause & exit /b 2
)

echo.
echo ============================================
echo Build done.  dist\voice2ai\voice2ai.exe
echo ============================================
echo To test:  dist\voice2ai\voice2ai.exe
echo To distribute:  zip the entire dist\voice2ai\ folder.
pause
