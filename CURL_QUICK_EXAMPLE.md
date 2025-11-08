# curl 导入配置 - 快速示例

## 最简单的方式：纯 Shell 命令

直接在服务器上执行以下命令即可导入配置：

```bash
# 从本地文件 frpc.ini 导入配置
curl -X POST "http://localhost:8000/api/config/import/text" \
  -H "Authorization: Basic $(echo -n 'admin:admin' | base64)" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg content "$(cat frpc.ini)" \
    '{content: $content, format: "ini", frps_server_id: 1}')"
```

## 参数说明

- **URL**: 替换为你的 frp-agent 服务地址
- **认证**: `admin:admin` 替换为实际的用户名和密码
- **文件**: `frpc.ini` 替换为你的配置文件路径
- **格式**: `"ini"` 或 `"toml"`
- **服务器ID**: `1` 替换为目标 frps 服务器 ID

## 完整示例

```bash
#!/bin/bash

# 配置参数
API_URL="http://localhost:8000"
USERNAME="admin"
PASSWORD="admin"
CONFIG_FILE="frpc.ini"
FORMAT="ini"
SERVER_ID=1

# 导入配置
curl -X POST "${API_URL}/api/config/import/text" \
  -H "Authorization: Basic $(echo -n "${USERNAME}:${PASSWORD}" | base64)" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg content "$(cat ${CONFIG_FILE})" \
    "{content: \$content, format: \"${FORMAT}\", frps_server_id: ${SERVER_ID}}")"
```

## 测试结果

成功时返回：
```json
{
  "success": true,
  "message": "导入完成：新增 2 个，更新 0 个，失败 0 个",
  "stats": {
    "total": 2,
    "created": 2,
    "updated": 0,
    "failed": 0,
    "errors": []
  }
}
```

## 依赖说明

此命令需要以下工具（通常系统已安装）：
- `curl` - HTTP 客户端
- `jq` - JSON 处理工具（如未安装：`apt/yum/brew install jq`）
- `base64` - Base64 编码工具（通常系统自带）
- `cat` - 读取文件（系统自带）

## 也可以使用项目脚本

如果服务器上有 Python 或可以下载项目脚本：

```bash
# Python 脚本（自动处理认证）
./import_frpc_config.py frpc.ini --username admin --password admin

# Shell 脚本（需要提供 token）
TOKEN=$(echo -n 'admin:admin' | base64)
./import_frpc_config.sh frpc.ini $TOKEN
```

## 故障排除

### 1. 没有 jq 命令
```bash
# Ubuntu/Debian
sudo apt-get install jq

# CentOS/RHEL
sudo yum install jq

# macOS
brew install jq
```

### 2. 认证失败（401）
- 检查用户名密码是否正确
- 确认 Base64 编码正确

### 3. 服务器不存在（404）
- 确认 frps_server_id 是否正确
- 先通过 Web 界面查看服务器 ID

### 4. 端口冲突
- 配置文件中的 remote_port 已被占用
- 修改端口号或删除冲突的代理

## 更多信息

- 完整文档：项目目录下的 `README.md`
- 在 Web 界面点击"导入配置"按钮查看示例

