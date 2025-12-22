@echo off
chcp 65001 >nul

echo ==============================
echo frp-agent 前端依赖安装
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

echo.
echo 安装前端依赖...
cd frontend
call npm install
cd ..

echo.
echo ==============================
echo ✅ 前端依赖安装完成！
echo ==============================
echo.
echo 启动前端开发服务器：
echo   dev-frontend.bat
echo.

pause

