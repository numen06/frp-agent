# 主机资源管理

主机资源分为两种互相独立的类型：

- **SSH 主机**：通过 SSH 密码或私钥访问，可执行远程命令。
- **Docker 主机**：通过 Portainer HTTP API 访问，可查询、启动、停止和重启容器。

两类资源共用系统用户、API Key 授权和访问审计，但不会共用连接方式或凭据。

## SSH 主机

1. 在“主机资源”中选择“添加主机 → SSH 主机”。
2. 填写主机名、地址和 SSH 端口。
3. 新建或选择 SSH 密码/私钥凭据。
4. 执行一次“连接测试”。首次连接会以 TOFU 方式记录 `SHA256:` 主机指纹，后续连接必须匹配该指纹。

同一个 SSH 凭据可以复用于多台主机，获授权的系统用户和 API Key 不会获得主机真实密码或私钥。

## Docker / Portainer 主机

1. 在 Portainer 创建 Access Token（推荐），也可以使用 Portainer 用户名和密码。
2. 添加 Docker 主机，填写 Portainer 地址和端口。默认 HTTPS 端口通常是 `9443`。
3. 填写 Portainer Endpoint ID。它是 Portainer 中对应环境的数字 ID，可在环境页面 URL 或 Portainer API 中查看。
4. 选择 Portainer API Key/密码凭据，并根据部署情况配置 TLS 校验或自定义 CA 证书。

系统通过以下 Portainer API 访问 Docker 环境：

```text
GET  /api/endpoints/{endpointId}
GET  /api/endpoints/{endpointId}/docker/containers/json?all=true
POST /api/endpoints/{endpointId}/docker/containers/{container}/start
POST /api/endpoints/{endpointId}/docker/containers/{container}/stop
POST /api/endpoints/{endpointId}/docker/containers/{container}/restart
```

不需要将 Docker Engine 的 `2375/2376` 端口直接暴露给本系统。

## 授权

管理员可以把主机授权给系统用户或 API Key，并分别启用：

- 连接测试
- SSH 命令执行
- Docker 容器操作

普通用户和 API Key 只能看到已授权的主机。API Key 使用 Bearer 认证：

```bash
curl -H "Authorization: Bearer <API_KEY>" \
  https://frp-agent.example/api/managed-hosts

curl -X POST \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"command":"uptime","timeout":30}' \
  https://frp-agent.example/api/managed-hosts/<HOST_ID>/commands
```

## 原生 SSH 跳板端口

系统默认在 `2222` 端口启动原生 SSH 网关。用户需要拥有目标 SSH 主机的“SSH 命令”权限。

使用系统用户和该用户自己的系统密码：

```bash
ssh -p 2222 '系统用户#SSH主机名'@frp-agent.example
```

使用 API Key：

```bash
# SSH 用户名直接填写主机名，认证密码填写已授权的 API Key
ssh -p 2222 'SSH主机名'@frp-agent.example

# 也支持显式形式
ssh -p 2222 'apikey#SSH主机名'@frp-agent.example
```

认证成功后，平台使用后台保存的 SSH 凭据连接目标主机并桥接交互终端。登录者不会得到目标主机密码或私钥。会话的登录者、来源 IP、目标主机、结果和持续时间会进入访问审计。

## Docker HTTPS 网关

系统默认在 `23750` 端口启动 Docker Engine API 兼容网关。它将请求转发到主机配置的 Portainer Endpoint，调用方需要拥有“Docker 操作”权限。

系统用户认证：

```bash
curl \
  -u '系统用户#Docker主机名:系统用户密码' \
  --cacert frp-agent-docker-gateway-ca.pem \
  'https://frp-agent.example:23750/containers/json?all=true'
```

API Key 认证：

```bash
curl \
  -u 'Docker主机名:API_KEY' \
  --cacert frp-agent-docker-gateway-ca.pem \
  'https://frp-agent.example:23750/containers/json?all=true'
```

也可以使用 Bearer 形式：

```bash
curl \
  -H 'Authorization: Bearer API_KEY' \
  -H 'X-Host: Docker主机名' \
  --cacert frp-agent-docker-gateway-ca.pem \
  'https://frp-agent.example:23750/containers/json?all=true'
```

Docker 网关只提供 HTTPS。首次启动时会在数据目录生成自签名 CA/服务端证书，可从主机资源页面下载。部署前应将 `DOCKER_GATEWAY_TLS_COMMON_NAME` 设置为客户端实际访问的域名或 IP。

## 安全配置

生产环境必须设置稳定、随机的 `SSH_CREDENTIAL_SECRET`。它同时保护 SSH 和 Portainer 凭据；修改该值后，已有凭据将无法解密。

```yaml
environment:
  - SSH_CREDENTIAL_SECRET=<至少 32 字节的随机值>
```

建议同时：

- 优先使用 Portainer API Key，避免长期保存 Portainer 登录密码。
- 保持 Portainer TLS 证书校验开启；自签名证书请配置 CA，不要直接关闭校验。
- 防火墙只向需要的网络开放 `2222` 和 `23750`，并妥善分发 Docker 网关 CA。
- SSH 凭据使用最小权限账号，并通过 `sudoers` 限制可执行命令。
- 定期检查“访问审计”，及时禁用不再使用的用户、API Key 和授权。
- 将应用数据目录纳入加密备份，并限制文件系统访问权限。
