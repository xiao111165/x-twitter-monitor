@echo off
chcp 65001 >nul
echo ==========================================
echo  X (Twitter) 账户监控器 - Windows 打包脚本
echo ==========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10 或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] 正在安装依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

echo [2/4] 正在安装 PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo [错误] PyInstaller 安装失败
    pause
    exit /b 1
)

echo [3/4] 正在打包为 EXE...
pyinstaller --onefile --windowed --name "X-Twitter-Monitor" main.py
if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo [4/4] 打包完成！
echo.
echo 可执行文件位置: dist\X-Twitter-Monitor.exe
echo.
pause
