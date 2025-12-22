@echo off
chcp 65001 >nul

echo ==============================
echo frp-agent 前端开发服务器
echo ==============================

REM 检查 Node.js 环境
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ 未找到 Node.js，请先安装 Node.js 18+
    echo    下载地址: https://nodejs.org/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
for /f "tokens=*" %%i in ('npm --version') do set NPM_VERSION=%%i
echo ✓ Node.js 已安装: %NODE_VERSION%
echo ✓ npm 已安装: %NPM_VERSION%

REM 检查前端目录
if not exist "frontend" (
    echo ❌ 未找到 frontend 目录
    pause
    exit /b 1
)

REM 检查 package.json
if not exist "frontend\package.json" (
    echo ❌ 未找到 frontend\package.json
    pause
    exit /b 1
)

REM 检查 node_modules
if not exist "frontend\node_modules" (
    echo ⚠ 前端依赖未安装，正在安装...
    cd frontend
    call npm install
    cd ..
    echo ✓ 依赖安装完成
) else (
    echo ✓ 前端依赖已安装
)

echo.
echo ==============================
echo 启动前端开发服务器...
echo ==============================
echo.
echo 📍 前端地址: http://localhost:5173
echo 🔗 API 代理: http://localhost:8000
echo.
echo 按 Ctrl+C 停止服务器
echo ==============================
echo.

REM 启动前端开发服务器
cd frontend
call npm run dev

