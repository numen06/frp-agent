# frp-agent 管理系统

基于 Python FastAPI 的 frp 代理管理系统，提供端口管理、冲突检测、配置生成等功能。

## 功能特性

- **多服务器支持**：支持配置和管理多个 frps 服务器
- **端口管理**：自动跟踪端口分配，检测端口冲突
- **状态同步**：定时从 frps API 同步代理状态
- **配置生成**：生成标准的 frpc.toml 配置文件和启动脚本
- **配置导入**：支持导入现有的 frpc 配置文件（INI/TOML），支持 curl 和脚本提交
- **历史记录**：记录代理上下线、端口分配等历史事件
- **Web 界面**：提供简洁的管理界面和 REST API

## 技术栈

- **后端**：FastAPI + SQLAlchemy
- **数据库**：SQLite
- **前端**：Bootstrap 5 + JavaScript
- **认证**：HTTP Basic Auth

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

访问 http://localhost:8000 进入管理界面。

📚 详细的 Docker 部署指南请查看 [DOCKER.md](DOCKER.md)

### 方式二：本地开发部署

#### 1. 一键初始化

```bash
# Linux/Mac
./init.sh

# Windows
init.bat
```

初始化脚本会自动完成以下操作：
- 创建虚拟环境
- 安装依赖
- 创建数据目录
- 初始化数据库
- 运行数据库迁移

#### 2. 启动应用

```bash
# 直接启动（推荐）
python app.py

# 或者先激活虚拟环境再启动
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
python app.py
```

#### 3. 配置环境变量（可选）

创建 `.env` 文件自定义配置：

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

访问 http://localhost:8000 进入管理界面。

## 主要功能

- **登录认证** - 自定义登录页面，保护系统安全
- **服务器管理** - 添加、编辑、测试 frps 服务器
- **代理管理** - 创建和管理 frp 代理配置
- **端口管理** - 自动分配和检测端口冲突
- **状态监测** - 实时监测服务器连接状态
- **配置生成** - 一键生成 frpc 配置文件
- **配置导入** - 导入现有 frpc.ini 或 frpc.toml 配置文件（支持 Web 上传和 API 调用）
- **用户设置** - 修改登录密码

## 主要 API 端点

### frps 服务器管理
- `GET /api/servers` - 获取服务器列表
- `POST /api/servers` - 添加服务器
- `PUT /api/servers/{id}` - 更新服务器
- `DELETE /api/servers/{id}` - 删除服务器

### 代理管理
- `GET /api/proxies` - 获取代理列表
- `POST /api/proxies` - 创建代理
- `GET /api/proxies/{id}` - 获取代理详情
- `PUT /api/proxies/{id}` - 更新代理
- `DELETE /api/proxies/{id}` - 删除代理

### 端口管理
- `GET /api/ports` - 查询端口使用情况
- `POST /api/ports/allocate` - 分配端口
- `POST /api/ports/release` - 释放端口

### 配置生成与导入
- `POST /api/config/generate` - 生成 frpc 配置文件
- `POST /api/config/import` - 导入配置文件（文件上传）
- `POST /api/config/import/{format}/{server_name}` - 导入配置文件（**最简洁，推荐！**）
- `POST /api/config/import/text` - 导入配置文件（JSON 提交）

### 同步
- `POST /api/sync` - 手动触发同步

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

### 其他导入方式

```bash
# 使用 Python 脚本
./import_frpc_config.py frpc.ini --username admin --password admin

# 使用 Shell 脚本
./import_frpc_config.sh frpc.ini $(echo -n 'admin:admin' | base64)
```

### 查看服务器名称

```bash
curl -u admin:admin http://localhost:8000/api/servers | jq '.[].name'
```

## 默认账号

- 用户名：`admin`
- 密码：`admin`

## 许可证

MIT License

