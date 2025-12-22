#!/bin/bash
# VSCode 环境安装脚本 (Bash)
# 用于 Linux/macOS 系统

echo "========================================"
echo "FRP Agent 环境安装脚本"
echo "========================================"

# 检查 Python 是否安装
echo ""
echo "[1/6] 检查 Python 环境..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✓ Python 已安装: $PYTHON_VERSION"
else
    echo "✗ Python 未安装，请先安装 Python 3.8+"
    exit 1
fi

# 检查 Node.js 是否安装
echo ""
echo "[2/6] 检查 Node.js 环境..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    NPM_VERSION=$(npm --version)
    echo "✓ Node.js 已安装: $NODE_VERSION"
    echo "✓ npm 已安装: $NPM_VERSION"
else
    echo "✗ Node.js 未安装，请先安装 Node.js 18+"
    echo "  下载地址: https://nodejs.org/"
    exit 1
fi

# 创建虚拟环境
echo ""
echo "[3/6] 创建 Python 虚拟环境..."
if [ -d "venv" ]; then
    echo "✓ 虚拟环境已存在"
else
    python3 -m venv venv
    echo "✓ 虚拟环境创建成功"
fi

# 激活虚拟环境并安装依赖
echo ""
echo "[4/6] 安装 Python 依赖..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install debugpy
echo "✓ Python 依赖安装完成"

# 安装 Node.js 依赖
echo ""
echo "[5/6] 安装 Node.js 依赖..."
if [ -f "frontend/package.json" ]; then
    cd frontend
    npm install
    cd ..
    echo "✓ Node.js 依赖安装完成"
else
    echo "⚠ 未找到 frontend/package.json，跳过 Node.js 依赖安装"
fi

# 初始化数据库
echo ""
echo "[6/6] 初始化数据库..."
if [ -f "app/init_db.py" ]; then
    python app/init_db.py
    echo "✓ 数据库初始化完成"
else
    echo "⚠ 未找到 init_db.py，跳过数据库初始化"
fi

echo ""
echo "========================================"
echo "环境安装完成！"
echo "========================================"
echo ""
echo "使用说明:"
echo "1. 在 VSCode 中按 F5 开始调试"
echo "   - 选择 'Python: FastAPI 应用' 调试后端"
echo "   - 选择 'Node.js: 调试 Vite 开发服务器' 调试前端"
echo "   - 选择 '复合: 前后端同时调试' 同时调试前后端"
echo "2. 使用 Ctrl+Shift+P 运行任务 (Tasks: Run Task)"
echo "   - '运行 FastAPI 应用' 启动后端服务"
echo "   - '运行前端开发服务器' 启动前端服务"
echo "   - '安装所有依赖' 安装前后端所有依赖"
echo ""

