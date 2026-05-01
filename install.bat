@echo off
chcp 65001 >nul
cd /d %~dp0
echo Voice2CC - 安装依赖
echo.
python -m pip install -r requirements.txt
echo.
echo ================================
echo 安装完成。运行 start.bat 启动。
echo ================================
pause
