#!/bin/bash

# frp-agent 前端开发启动脚本

echo "=============================="
echo "frp-agent 前端开发服务器"
echo "=============================="

# 检查 Node.js 环境
if ! command -v node &> /dev/null; then
    echo "❌ 未找到 Node.js，请先安装 Node.js 18+"
    echo "   下载地址: https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node --version)
NPM_VERSION=$(npm --version)
echo "✓ Node.js 已安装: $NODE_VERSION"
echo "✓ npm 已安装: $NPM_VERSION"

# 检查前端目录
if [ ! -d "frontend" ]; then
    echo "❌ 未找到 frontend 目录"
    exit 1
fi

# 检查 package.json
if [ ! -f "frontend/package.json" ]; then
    echo "❌ 未找到 frontend/package.json"
    exit 1
fi

# 检查 node_modules
if [ ! -d "frontend/node_modules" ]; then
    echo "⚠ 前端依赖未安装，正在安装..."
    cd frontend
    npm install
    cd ..
    echo "✓ 依赖安装完成"
else
    echo "✓ 前端依赖已安装"
fi

echo ""
echo "=============================="
echo "启动前端开发服务器..."
echo "=============================="
echo ""
echo "📍 前端地址: http://localhost:5173"
echo "🔗 API 代理: http://localhost:8000"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "=============================="
echo ""

# 启动前端开发服务器
cd frontend
npm run dev

