@echo off
chcp 65001 >nul
cd /d %~dp0
title voice2cc

REM Use pythonw if available so no console window flashes for non-developers.
where pythonw >nul 2>nul
if errorlevel 1 (
    python app.py
) else (
    pythonw app.py
)
