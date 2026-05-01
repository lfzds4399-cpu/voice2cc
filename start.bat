@echo off
chcp 65001 >nul
cd /d %~dp0
title Voice2CC
python voice2cc.py
pause
