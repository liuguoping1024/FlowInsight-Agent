@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo FlowInsight MCP 配置工具 - Claude Desktop App
echo ============================================================
echo.

REM 获取当前脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM 获取 Python 路径（默认使用 C:\Python313\python.exe）
set "PYTHON_PATH=C:\Python313\python.exe"

REM 检查 Python 是否存在
if not exist "%PYTHON_PATH%" (
    echo [错误] 未找到 Python: %PYTHON_PATH%
    echo 请修改此脚本中的 PYTHON_PATH 变量为您的 Python 路径
    pause
    exit /b 1
)

echo [信息] Python 路径: %PYTHON_PATH%
echo [信息] 项目目录: %SCRIPT_DIR%
echo.

REM Claude Desktop 配置目录
set "CLAUDE_CONFIG_DIR=%APPDATA%\Claude"
set "CLAUDE_CONFIG_FILE=%CLAUDE_CONFIG_DIR%\claude_desktop_config.json"

echo [信息] Claude 配置目录: %CLAUDE_CONFIG_DIR%
echo [信息] 配置文件: %CLAUDE_CONFIG_FILE%
echo.

REM 检查配置目录是否存在
if not exist "%CLAUDE_CONFIG_DIR%" (
    echo [信息] 创建配置目录...
    mkdir "%CLAUDE_CONFIG_DIR%"
)

REM 检查配置文件是否存在
if not exist "%CLAUDE_CONFIG_FILE%" (
    echo [信息] 创建新的配置文件...
    echo {} > "%CLAUDE_CONFIG_FILE%"
)

REM 读取现有配置
echo [信息] 读取现有配置...
python -c "import json, sys; data = json.load(open(r'%CLAUDE_CONFIG_FILE%', 'r', encoding='utf-8')) if open(r'%CLAUDE_CONFIG_FILE%', 'r', encoding='utf-8').read().strip() else {}; print(json.dumps(data, indent=2, ensure_ascii=False))" > "%TEMP%\claude_config_temp.json" 2>nul
if errorlevel 1 (
    echo [警告] 无法读取现有配置，将创建新配置
    set "EXISTING_CONFIG={}"
) else (
    set /p EXISTING_CONFIG=<"%TEMP%\claude_config_temp.json"
)

REM 构建 MCP 服务器配置
echo [信息] 配置 MCP 服务器...

REM 转换路径中的反斜杠为正斜杠（JSON 需要）
set "MCP_SERVER_PATH=%SCRIPT_DIR%\mcp_stdio_server.py"
set "MCP_SERVER_PATH=!MCP_SERVER_PATH:\=/!"

REM 创建新的配置（设置工作目录为项目目录）
python -c "import json, sys, os; config_file = r'%CLAUDE_CONFIG_FILE%'; script_dir = r'%SCRIPT_DIR%'; python_path = r'%PYTHON_PATH%'; existing = {}; \
if os.path.exists(config_file) and os.path.getsize(config_file) > 0: \
    with open(config_file, 'r', encoding='utf-8') as f: \
        try: existing = json.load(f); \
        except: pass; \
if 'mcpServers' not in existing: existing['mcpServers'] = {}; \
existing['mcpServers']['flowinsight'] = { \
    'command': python_path, \
    'args': [os.path.join(script_dir, 'mcp_stdio_server.py')], \
    'cwd': script_dir, \
    'env': {} \
}; \
with open(config_file, 'w', encoding='utf-8') as f: \
    json.dump(existing, f, indent=2, ensure_ascii=False); \
print('配置已更新')"

if errorlevel 1 (
    echo [错误] 配置更新失败
    pause
    exit /b 1
)

echo.
echo [成功] MCP 配置已完成！
echo.
echo ============================================================
echo 配置详情:
echo ============================================================
echo MCP 服务器名称: flowinsight
echo Python 路径: %PYTHON_PATH%
echo MCP 服务器脚本: %SCRIPT_DIR%\mcp_stdio_server.py
echo 配置文件: %CLAUDE_CONFIG_FILE%
echo.
echo ============================================================
echo 下一步:
echo ============================================================
echo 1. 重启 Claude Desktop App
echo 2. 在 Claude Desktop 中，您应该能看到 "flowinsight" MCP 服务器
echo 3. 可以使用以下工具:
echo    - get_stock_list: 获取股票列表
echo    - get_stock_health: 获取股票健康度
echo    - get_stock_history: 获取股票历史数据
echo    - sync_stock_list: 同步股票列表
echo    - sync_stock_history: 同步股票历史数据
echo    - 等等...
echo.
echo ============================================================
echo 配置文件内容预览:
echo ============================================================
type "%CLAUDE_CONFIG_FILE%"
echo.
echo ============================================================
pause

