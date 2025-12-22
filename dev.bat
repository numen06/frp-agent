@echo off
chcp 65001 >nul

echo ==============================
echo frp-agent 后端开发服务器
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
    echo ⚠ 虚拟环境不存在，请先运行 init.bat 初始化项目
    pause
    exit /b 1
)

echo ✓ 虚拟环境已存在

REM 激活虚拟环境
echo 激活虚拟环境...
call venv\Scripts\activate.bat

REM 检查依赖是否安装
python -c "import fastapi" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ⚠ Python 依赖未安装，正在安装...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    echo ✓ 依赖安装完成
) else (
    echo ✓ Python 依赖已安装
)

REM 创建数据目录
if not exist "data" (
    echo 创建数据目录...
    mkdir data
    echo ✓ 数据目录创建成功
)

REM 检查数据库是否存在
if not exist "data\frp_agent.db" (
    echo ⚠ 数据库不存在，正在初始化...
    cd backend
    python -m app.init_db
    cd ..
    echo ✓ 数据库初始化完成
)

echo.
echo ==============================
echo 启动后端开发服务器...
echo ==============================
echo.
echo 📍 API 地址: http://localhost:8000
echo 📖 API 文档: http://localhost:8000/docs
echo 🎛️  管理界面: http://localhost:8000/dashboard
echo.
echo 按 Ctrl+C 停止服务器
echo ==============================
echo.

REM 启动后端服务
cd backend
python app.py

