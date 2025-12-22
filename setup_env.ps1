# VSCode 环境安装脚本 (PowerShell)
# 用于 Windows 系统

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FRP Agent 环境安装脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 检查 Python 是否安装
Write-Host "`n[1/6] 检查 Python 环境..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python 已安装: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python 未安装，请先安装 Python 3.8+" -ForegroundColor Red
    exit 1
}

# 检查 Node.js 是否安装
Write-Host "`n[2/6] 检查 Node.js 环境..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    $npmVersion = npm --version 2>&1
    Write-Host "✓ Node.js 已安装: $nodeVersion" -ForegroundColor Green
    Write-Host "✓ npm 已安装: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Node.js 未安装，请先安装 Node.js 18+" -ForegroundColor Red
    Write-Host "  下载地址: https://nodejs.org/" -ForegroundColor Yellow
    exit 1
}

# 创建虚拟环境
Write-Host "`n[3/6] 创建 Python 虚拟环境..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "✓ 虚拟环境已存在" -ForegroundColor Green
} else {
    python -m venv venv
    Write-Host "✓ 虚拟环境创建成功" -ForegroundColor Green
}

# 激活虚拟环境并安装依赖
Write-Host "`n[4/6] 安装 Python 依赖..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install debugpy
Write-Host "✓ Python 依赖安装完成" -ForegroundColor Green

# 安装 Node.js 依赖
Write-Host "`n[5/6] 安装 Node.js 依赖..." -ForegroundColor Yellow
if (Test-Path "frontend\package.json") {
    Set-Location frontend
    npm install
    Set-Location ..
    Write-Host "✓ Node.js 依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "⚠ 未找到 frontend/package.json，跳过 Node.js 依赖安装" -ForegroundColor Yellow
}

# 初始化数据库
Write-Host "`n[6/6] 初始化数据库..." -ForegroundColor Yellow
if (Test-Path "app\init_db.py") {
    python app\init_db.py
    Write-Host "✓ 数据库初始化完成" -ForegroundColor Green
} else {
    Write-Host "⚠ 未找到 init_db.py，跳过数据库初始化" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "环境安装完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`n使用说明:" -ForegroundColor Yellow
Write-Host "1. 在 VSCode 中按 F5 开始调试" -ForegroundColor White
Write-Host "   - 选择 'Python: FastAPI 应用' 调试后端" -ForegroundColor White
Write-Host "   - 选择 'Node.js: 调试 Vite 开发服务器' 调试前端" -ForegroundColor White
Write-Host "   - 选择 '复合: 前后端同时调试' 同时调试前后端" -ForegroundColor White
Write-Host "2. 使用 Ctrl+Shift+P 运行任务 (Tasks: Run Task)" -ForegroundColor White
Write-Host "   - '运行 FastAPI 应用' 启动后端服务" -ForegroundColor White
Write-Host "   - '运行前端开发服务器' 启动前端服务" -ForegroundColor White
Write-Host "   - '安装所有依赖' 安装前后端所有依赖" -ForegroundColor White
Write-Host "`n按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

