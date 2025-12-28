@echo off
chcp 65001 >nul
echo ========================================
echo FlowInsight-Agent 数据库初始化
echo ========================================
echo.

REM 使用指定的Python路径
set PYTHON_PATH=C:\Python313\python.exe

REM 检查Python是否存在
if not exist "%PYTHON_PATH%" (
    echo ❌ Python未找到: %PYTHON_PATH%
    echo 请检查Python安装路径
    pause
    exit /b 1
)

echo 使用Python: %PYTHON_PATH%
echo.

REM 执行初始化脚本
"%PYTHON_PATH%" init_database.py

echo.
pause

