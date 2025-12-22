#!/bin/bash

# frp-agent 初始化脚本

echo "=============================="
echo "frp-agent 初始化"
echo "=============================="

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python 3，请先安装"
    exit 1
fi

echo "✓ Python 3 已安装"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
    echo "✓ 虚拟环境创建成功"
else
    echo "✓ 虚拟环境已存在"
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 安装/更新依赖
echo "安装依赖..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ 依赖安装完成"

# 创建数据目录
if [ ! -d "data" ]; then
    echo "创建数据目录..."
    mkdir -p data
    echo "✓ 数据目录创建成功"
else
    echo "✓ 数据目录已存在"
fi

# 检查数据库是否存在
if [ ! -f "data/frp_agent.db" ]; then
    echo "初始化数据库..."
    cd backend
    python -m app.init_db
    cd ..
    echo "✓ 数据库初始化完成"
else
    echo "✓ 数据库已存在"
    echo "提示：如需重新初始化，请删除 data/frp_agent.db 文件"
fi

# 运行数据库迁移
echo "检查数据库迁移..."
cd backend
python -m app.migrations.add_server_test_fields
cd ..
echo ""

echo "=============================="
echo "✅ 初始化完成！"
echo "=============================="
echo ""
echo "启动应用："
echo "  方式1: cd backend && python app.py"
echo "  方式2: python backend/app.py"
echo "  方式3: python run.py"
echo ""
echo "访问地址："
echo "  管理界面: http://localhost:8000/dashboard"
echo "  API 文档: http://localhost:8000/docs"
echo ""
echo "默认账号："
echo "  用户名: admin"
echo "  密码: admin"
echo "=============================="

