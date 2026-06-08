@echo off
chcp 65001 >nul
title X-Twitter-Monitor 一键安装打包工具
color 0A
cls

echo ============================================
echo    X (Twitter) 账户监控器 - 一键安装打包工具
echo ============================================
echo.
echo 本工具将自动完成以下操作：
echo   1. 下载并安装 Python
echo   2. 安装所需依赖
echo   3. 打包为可执行文件
echo.
echo 请按任意键开始...
pause >nul
cls

REM 检查是否已安装 Python
python --version >nul 2>&1
if %errorlevel% == 0 (
    echo [✓] 检测到已安装 Python
    goto INSTALL_DEPS
)

echo [*] 正在下载 Python 安装程序...
echo   下载地址: https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
curl -L -o python_installer.exe https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
if not exist python_installer.exe (
    echo [✗] 下载失败，请检查网络连接
    pause
    exit /b 1
)

echo [*] 正在安装 Python（请等待，可能需要几分钟）...
start /wait python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
if %errorlevel% neq 0 (
    echo [✗] Python 安装失败
    pause
    exit /b 1
)

echo [✓] Python 安装完成
echo [*] 正在刷新环境变量...
timeout /t 3 /nobreak >nul

del python_installer.exe

:INSTALL_DEPS
echo.
echo [*] 正在安装依赖库（约需 2-3 分钟）...
pip install twitscraper ttkbootstrap pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo [✗] 依赖安装失败，尝试使用默认源...
    pip install twitscraper ttkbootstrap pyinstaller
)

echo.
echo [*] 正在打包为可执行文件（约需 3-5 分钟）...
pyinstaller --onefile --windowed --name "X-Twitter-Monitor" --clean main.py
if %errorlevel% neq 0 (
    echo [✗] 打包失败
    pause
    exit /b 1
)

echo.
echo ============================================
echo    [✓] 打包完成！
echo ============================================
echo.
echo 可执行文件位置:
echo   %CD%\dist\X-Twitter-Monitor.exe
echo.
echo 您可以将此文件复制到任意位置使用。
echo.
pause
