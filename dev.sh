#!/bin/bash

# frp-agent 后端开发启动脚本

echo "=============================="
echo "frp-agent 后端开发服务器"
echo "=============================="

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python 3，请先安装"
    exit 1
fi

echo "✓ Python 3 已安装"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "⚠ 虚拟环境不存在，请先运行 ./init.sh 初始化项目"
    exit 1
fi

echo "✓ 虚拟环境已存在"

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 检查依赖是否安装
if ! python -c "import fastapi" &> /dev/null; then
    echo "⚠ Python 依赖未安装，正在安装..."
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "✓ 依赖安装完成"
else
    echo "✓ Python 依赖已安装"
fi

# 创建数据目录
if [ ! -d "data" ]; then
    echo "创建数据目录..."
    mkdir -p data
    echo "✓ 数据目录创建成功"
fi

# 检查数据库是否存在
if [ ! -f "data/frp_agent.db" ]; then
    echo "⚠ 数据库不存在，正在初始化..."
    cd backend
    python -m app.init_db
    cd ..
    echo "✓ 数据库初始化完成"
fi

echo ""
echo "=============================="
echo "启动后端开发服务器..."
echo "=============================="
echo ""
echo "📍 API 地址: http://localhost:8000"
echo "📖 API 文档: http://localhost:8000/docs"
echo "🎛️  管理界面: http://localhost:8000/dashboard"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "=============================="
echo ""

# 启动后端服务
cd backend
python app.py

