# 直接配置访问功能使用指南

## 功能概述

新增了通过 URL 直接访问配置文件的功能，支持在 URL 中包含认证信息，方便在 Linux 服务器上一键安装 frpc。

## 主要特性

1. **配置文件直接下载**：通过 URL + Basic Auth 直接下载配置文件
2. **一键安装脚本**：自动从服务器拉取配置并安装
3. **配置自动更新**：安装脚本会生成配置更新脚本，方便后续更新
4. **前端集成**：在生成配置界面直接显示可复制的 URL 和安装命令

## API 接口

### 1. 直接获取配置文件

**接口地址**：`GET /api/frpc/config/direct/{group_name}`

**认证方式**：HTTP Basic Auth

**参数**：
- `group_name`：分组名称（路径参数）
- `frps_server_id`：frps 服务器 ID（查询参数，必填）
- `format`：配置格式，ini 或 toml（查询参数，可选，默认 ini）

**使用示例**：

```bash
# 使用 -u 参数指定用户名和密码
curl -u admin:password "http://your-server.com/api/frpc/config/direct/dlyy?frps_server_id=1" -o frpc.ini

# 或者在 URL 中包含认证信息
curl "http://admin:password@your-server.com/api/frpc/config/direct/dlyy?frps_server_id=1" -o frpc.ini
```

### 2. 直接获取安装脚本

**接口地址**：`GET /api/frpc/install-script/direct/{group_name}`

**认证方式**：HTTP Basic Auth

**参数**：
- `group_name`：分组名称（路径参数）
- `frps_server_id`：frps 服务器 ID（查询参数，必填）
- `install_path`：安装路径（查询参数，可选，默认 /opt/frp）

**使用示例**：

```bash
# 一键安装（推荐）
curl -u admin:password "http://your-server.com/api/frpc/install-script/direct/dlyy?frps_server_id=1" | sudo bash

# 或者先下载再执行
curl -u admin:password "http://your-server.com/api/frpc/install-script/direct/dlyy?frps_server_id=1" -o install.sh
chmod +x install.sh
sudo ./install.sh
```

## 前端使用

在前端界面中，当生成配置文件或安装脚本时，会自动显示：

1. **配置文件下载地址**：可直接复制的 URL
2. **一键安装命令**：可直接在 Linux 服务器上执行的完整命令
3. **使用说明**：详细的使用步骤

### 界面位置

- **代理列表页面**：选择代理 → 生成配置 → 查看配置/脚本
- **分组管理页面**：选择分组 → 生成配置 → 查看配置/脚本

## 安装脚本功能

生成的安装脚本包含以下功能：

1. **自动下载 frpc**：根据系统架构自动下载对应版本的 frpc
2. **从 API 获取配置**：使用认证从 API 自动下载最新配置
3. **创建 systemd 服务**：自动创建并启动 frpc 服务
4. **生成更新脚本**：在 `/opt/frp/update_config.sh` 生成配置更新脚本

### 配置更新

安装完成后，如果配置文件在服务器上更新了，可以执行以下命令更新本地配置：

```bash
# 更新配置文件并重启服务
sudo /opt/frp/update_config.sh
```

### 服务管理

安装完成后，可以使用以下命令管理 frpc 服务：

```bash
# 查看服务状态
systemctl status frpc

# 查看实时日志
journalctl -u frpc -f

# 重启服务
systemctl restart frpc

# 停止服务
systemctl stop frpc

# 启动服务
systemctl start frpc
```

## 安全注意事项

1. **密码保护**：确保使用强密码，不要在公开场合暴露包含密码的 URL
2. **HTTPS**：生产环境建议使用 HTTPS 加密传输
3. **防火墙**：确保 API 服务器的防火墙配置正确
4. **定期更新密码**：定期更换认证密码以提高安全性

## 文件位置

### 安装路径

默认安装路径：`/opt/frp/`

文件结构：
```
/opt/frp/
├── frpc              # frpc 可执行文件
├── frpc.ini          # 配置文件
└── update_config.sh  # 配置更新脚本
```

### 服务配置

systemd 服务文件：`/etc/systemd/system/frpc.service`

## 故障排查

### 配置下载失败

如果配置下载失败，请检查：

1. 用户名和密码是否正确
2. API 服务器地址是否可访问
3. frps_server_id 是否正确
4. 分组名称是否存在

### 服务启动失败

如果服务启动失败，请检查：

1. frpc 配置文件是否正确
2. 本地端口是否被占用
3. frps 服务器地址是否可达
4. 查看服务日志：`journalctl -u frpc -n 50`

## 示例场景

### 场景 1：新服务器快速部署

```bash
# 在新的 Linux 服务器上执行一条命令即可完成部署
curl -u admin:your_password "http://your-api.com/api/frpc/install-script/direct/production?frps_server_id=1" | sudo bash
```

### 场景 2：批量部署多台服务器

创建一个部署脚本 `deploy.sh`：

```bash
#!/bin/bash

# 服务器列表
SERVERS=(
    "192.168.1.10"
    "192.168.1.11"
    "192.168.1.12"
)

# API 配置
API_URL="http://your-api.com"
USERNAME="admin"
PASSWORD="your_password"
GROUP_NAME="production"
SERVER_ID="1"

for server in "${SERVERS[@]}"; do
    echo "正在部署到 $server ..."
    ssh root@$server "curl -u $USERNAME:$PASSWORD '$API_URL/api/frpc/install-script/direct/$GROUP_NAME?frps_server_id=$SERVER_ID' | bash"
done
```

### 场景 3：配置文件更新

当修改了配置后，在所有客户端执行：

```bash
# 单台服务器
sudo /opt/frp/update_config.sh

# 批量更新（使用 SSH）
for server in 192.168.1.{10..20}; do
    ssh root@$server "/opt/frp/update_config.sh"
done
```

## 更新日志

- **2024-11-08**：初始版本发布
  - 添加 Basic Auth 认证的配置获取接口
  - 添加一键安装脚本接口
  - 前端集成显示 URL 和安装命令
  - 支持配置自动更新


