@echo off
chcp 65001 >nul

echo ==============================
echo frp-agent 初始化
echo ==============================

REM 检查 Python 环境
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ 未找到 Python，请先安装
    pause
    exit /b 1
)

echo ✓ Python 已安装

REM 检查虚拟环境
if not exist "venv" (
    echo 创建虚拟环境...
    python -m venv venv
    echo ✓ 虚拟环境创建成功
) else (
    echo ✓ 虚拟环境已存在
)

REM 激活虚拟环境
echo 激活虚拟环境...
call venv\Scripts\activate.bat

REM 安装/更新依赖
echo 安装依赖...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo ✓ 依赖安装完成

REM 创建数据目录
if not exist "data" (
    echo 创建数据目录...
    mkdir data
    echo ✓ 数据目录创建成功
) else (
    echo ✓ 数据目录已存在
)

REM 检查数据库是否存在
if not exist "data\frp_agent.db" (
    echo 初始化数据库...
    python -m app.init_db
    echo ✓ 数据库初始化完成
) else (
    echo ✓ 数据库已存在
    echo 提示：如需重新初始化，请删除 data\frp_agent.db 文件
)

REM 运行数据库迁移
echo 检查数据库迁移...
python -m app.migrations.add_server_test_fields
echo.

echo ==============================
echo ✅ 初始化完成！
echo ==============================
echo.
echo 启动应用：
echo   方式1: python app.py
echo   方式2: venv\Scripts\activate ^&^& python app.py
echo.
echo 访问地址：
echo   管理界面: http://localhost:8000/dashboard
echo   API 文档: http://localhost:8000/docs
echo.
echo 默认账号：
echo   用户名: admin
echo   密码: admin@123
echo ==============================

pause

