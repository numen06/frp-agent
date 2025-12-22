# frp-agent 管理系统

基于 Vue 3 + Vite + FastAPI 的 frp 代理管理系统，提供端口管理、冲突检测、配置生成等功能。

## 功能特性

- **多服务器支持**：支持配置和管理多个 frps 服务器
- **端口管理**：自动跟踪端口分配，检测端口冲突
- **状态同步**：定时从 frps API 同步代理状态
- **配置生成**：生成标准的 frpc.toml 配置文件和启动脚本
- **配置导入**：支持导入现有的 frpc 配置文件（INI/TOML），支持 curl 和脚本提交
- **历史记录**：记录代理上下线、端口分配等历史事件
- **现代化 Web 界面**：基于 Vue 3 + Element Plus 的响应式管理界面

## 技术栈

- **前端**：Vue 3 + Vite + Vue Router + Pinia + Element Plus
- **后端**：FastAPI + SQLAlchemy
- **数据库**：SQLite
- **认证**：HTTP Basic Auth
- **部署**：Docker + Nginx

## 项目结构

```
frp-agent/
├── backend/              # 后端代码
│   ├── app/             # FastAPI 应用
│   └── requirements.txt # Python 依赖
├── frontend/            # 前端代码
│   ├── src/            # Vue 源代码
│   ├── package.json    # Node.js 依赖
│   └── vite.config.js  # Vite 配置
└── docker-compose.yml  # Docker Compose 配置
```

## 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone <repository-url>
cd frp-agent

# 2. 创建数据目录
mkdir -p data

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f
```

访问 http://localhost 进入管理界面。

### 方式二：本地开发部署

#### 后端启动

**⚠️ 重要**：主入口文件是 `backend/app.py`，不要从项目根目录直接运行 `uvicorn app.main:app`。

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境（可选）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动后端服务（推荐方式）
python app.py

# 或者从项目根目录运行辅助脚本
# python run.py
```

**其他启动方式**：
- 从项目根目录：`python run.py` 或 `python backend/app.py`
- 使用 uvicorn（需要在 backend 目录下）：`uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

详细启动指南请参考 [START.md](START.md)

后端服务将在 http://localhost:8000 启动。

#### 前端启动

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
```

前端开发服务器将在 http://localhost:5173 启动。

#### 配置环境变量（可选）

创建 `backend/.env` 文件自定义后端配置：

```bash
# 认证配置
AUTH_USERNAME=admin
AUTH_PASSWORD=admin

# 数据库配置
DATABASE_URL=sqlite:///./data/frp_agent.db

# 应用配置
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=false
```

创建 `frontend/.env.development` 文件自定义前端配置：

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## 主要功能

- **登录认证** - 安全的用户认证系统
- **服务器管理** - 添加、编辑、测试 frps 服务器
- **代理管理** - 创建和管理 frp 代理配置，支持批量操作
- **端口管理** - 自动分配和检测端口冲突
- **状态监测** - 实时监测服务器连接状态
- **配置生成** - 一键生成 frpc 配置文件（INI/TOML）
- **配置导入** - 导入现有 frpc.ini 或 frpc.toml 配置文件（支持 Web 上传和 API 调用）
- **分组管理** - 管理代理分组，支持自动分析
- **INI 转 TOML** - 便捷的配置文件格式转换工具
- **用户设置** - 修改登录密码

## 主要 API 端点

### frps 服务器管理
- `GET /api/servers` - 获取服务器列表
- `POST /api/servers` - 添加服务器
- `PUT /api/servers/{id}` - 更新服务器
- `DELETE /api/servers/{id}` - 删除服务器
- `POST /api/servers/{id}/test` - 测试服务器连接

### 代理管理
- `GET /api/proxies` - 获取代理列表
- `POST /api/proxies` - 创建代理
- `GET /api/proxies/{id}` - 获取代理详情
- `PUT /api/proxies/{id}` - 更新代理
- `DELETE /api/proxies/{id}` - 删除代理
- `POST /api/proxies/batch-detect-ports` - 批量识别端口

### 分组管理
- `GET /api/groups` - 获取分组列表
- `POST /api/groups` - 创建分组
- `PUT /api/groups/{name}` - 更新分组（重命名）
- `DELETE /api/groups/{name}` - 删除分组
- `POST /api/groups/auto-analyze` - 自动分析分组

### 端口管理
- `GET /api/ports` - 查询端口使用情况
- `POST /api/ports/allocate` - 分配端口
- `POST /api/ports/release` - 释放端口

### 配置生成与导入
- `POST /api/config/generate` - 生成 frpc 配置文件
- `POST /api/config/import` - 导入配置文件（文件上传）
- `POST /api/config/import/{format}/{server_name}` - 导入配置文件（**最简洁，推荐！**）
- `POST /api/config/import/text` - 导入配置文件（JSON 提交）
- `POST /api/frpc/convert/ini-to-toml/direct` - INI 转 TOML

### 同步
- `POST /api/sync` - 手动触发同步

### 用户设置
- `GET /api/settings/user` - 获取用户设置
- `POST /api/settings/password` - 修改密码

## 配置导入功能

### 一行命令导入配置

```bash
curl -u admin:admin -X POST \
  -H "Content-Type: text/plain" \
  --data-binary "@frpc.ini" \
  http://localhost:8000/api/config/import/ini/服务器名
```

### 实际使用示例

```bash
# 导入 INI 配置到 51jbm 服务器
curl -u admin:admin -X POST \
  -H "Content-Type: text/plain" \
  --data-binary "@frpc.ini" \
  http://localhost:8000/api/config/import/ini/51jbm

# 导入 TOML 配置
curl -u admin:admin -X POST \
  -H "Content-Type: text/plain" \
  --data-binary "@frpc.toml" \
  http://localhost:8000/api/config/import/toml/prod_server
```

### 查看服务器名称

```bash
curl -u admin:admin http://localhost:8000/api/servers | jq '.[].name'
```

## 开发指南

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

### 后端开发

```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动服务（主入口文件）
python app.py

# 或者从项目根目录运行辅助脚本
python run.py
```

### 构建生产版本

```bash
# 前端构建
cd frontend
npm run build

# 构建产物在 frontend/dist 目录
```

## 默认账号

- 用户名：`admin`
- 密码：`admin`

## 许可证

MIT License
