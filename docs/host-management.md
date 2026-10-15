# 主机资源管理

主机资源分为三种互相独立的类型：

- **SSH 主机**：通过 SSH 密码或私钥访问，可执行远程命令。
- **Docker 主机**：通过 Portainer HTTP API 访问，可查询、启动、停止和重启容器。
- **RDP 主机**：通过本项目内置的 HTTPS 网关，使用 Windows 自带 mstsc 访问。

三类资源共用系统用户、API Key 授权和访问审计，但不会共用连接方式或凭据。

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
- RDP 远程桌面访问（使用“连接 / RDP 访问”权限）
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

## RDP 单端口网关（公网 TCP 13389）

RDP 沿用 SSH 的账号、主机路由、权限检查及加密凭据存储。客户端输入平台账号和平台密码，网关使用主机绑定的 Windows 密码凭据代登录。Windows 密码不会发给用户，不写入 `.rdp` 文件。

管理员新增 RDP 主机时填写网关可达的地址、端口、Windows 密码凭据，以及从可信链路取得的目标 RDP 证书 SHA-256 指纹（`SHA256:` 加 64 位十六进制）。本项目复用密码凭据表和 AES-GCM 加密实现，RDP 不接受 SSH 私钥。

Windows 自带 `mstsc` 的连接信息：

| 字段 | 内容 |
| --- | --- |
| 计算机 | `frpagent.51jbm.cn:13389` |
| 用户名 | `admin#haishi_win_rdp`（平台用户#资源名称） |
| 密码 | `admin` 的平台密码 |

普通用户需要该主机的“连接”授权，平台管理员可以连接启用的 RDP 主机。API Key 也复用 SSH 格式：用户名填写 RDP 资源名称（或 `apikey#资源名称`），密码填写获准连接该主机的 API Key。

也可在“主机管理”下载 `.rdp` 文件并双击，文件已填写公网地址和平台用户名。文件不含密码、票据或目标内网地址，可重复使用；每次连接均重新校验平台身份和主机权限。旧版 RD Gateway 短时票据文件不适用于此代理，应重新下载。

部署配置（默认关闭）：

```yaml
environment:
  - RDP_GATEWAY_ENABLED=true
  - RDP_GATEWAY_PORT=13389
  - RDP_GATEWAY_PUBLIC_ADDRESS=frpagent.51jbm.cn:13389
  - RDP_GATEWAY_TLS_CERT_PATH=/app/rdp-tls/cert.pem
  - RDP_GATEWAY_TLS_KEY_PATH=/app/rdp-tls/key.pem
  - RDP_GATEWAY_TRUSTED_PROXIES=172.25.0.2/32
ports:
  - "13389:13389"
```

容器镜像包含 FreeRDP 3.15.0 的 Debian 安全维护包（`3.15.0+dfsg-2.1+deb13u3`）及本项目的凭据映射模块。源码部署需要同版本的 `freerdp3-proxy`、开发头文件、libcurl、json-c 和 OpenSSL，模块使用 `gateway/rdp/proxy-frpagent.c`，构建命令见 Dockerfile。模块为必需插件，加载失败时不提供访问。代理仅监听随机回环端口，应用负责公网监听、限流及会话撤销。

安全边界：

- 客户端到网关强制 TLS 1.2 起、正式域名证书校验，拒绝旧式 RDP 加密。为兼容平台现有密码哈希认证，入口使用 TLS 内的 RDP 登录凭据，不启用入口 NLA；连接文件设置 `enablecredsspsupport:i:0`。目标 Windows 侧仍强制 NLA，不允许降级。
- 平台凭据通过 TLS 交给网关验证，目标 Windows 凭据仅由应用通过回环认证接口交给代理。内部接口要求随机密钥和真实前端连接关联，不接受公网调用。
- 目标只能由已认证用户的资源授权决定，拒绝客户端自定目标和 RDP 重定向。目标证书固定核对 SHA-256 指纹；更换证书需要管理员核验后更新。
- 每 IP 最多 8 条连接、全局最多 128 条；每 IP 每 5 分钟最多 60 次连接，5 分钟内认证失败 10 次后封禁 30 分钟；未认证连接 20 秒关闭，单会话最多 8 小时。
- 每 15 秒重查用户/API Key、主机、授权和平台/目标凭据；禁用、到期、撤权、修改密码、地址或目标证书时关闭已有连接。后台不可用时关闭连接。
- 剪贴板、磁盘、打印机、智能卡、音频、摄像头及 RemoteApp 重定向关闭，客户端无法请求额外透传通道。
- 审计区分平台授权、上游桌面连接完成和断开，不把平台授权成功当成 Windows 登录成功。审计不含密码、按键或桌面内容。
- 官网沿用现有认证，本次未新增 MFA。保留现有 SSH、Docker 网关；RDP 状态和限流保存在单进程内，不支持多个应用 worker 共享连接。

线上 Windows 试运行链路为公网网关 → 宿主机内网 `172.16.97.250:6094` → FRP → `10.81.73.29:3389`，资源名称 `haishi_win_rdp`（ID 8）。旧 `6094` 直连入口仍保留，正式收口需结合现有客户端迁移。

反代与应用共用外部 Docker 网络 `nginx-webui_default`，官网上游为 `tools-frp-agent-1:8005`，可信反代为 `172.25.0.2/32`。Portainer Stack 9 的持久化定义需要与部署配置同步。

无凭据 TLS 检查命令：

```powershell
.\.venv\Scripts\python.exe backend/scripts/verify_rdp_gateway.py frpagent.51jbm.cn 13389
```

此检查只确认 RDP/TLS 和域名证书，不宣称 Windows 登录成功；实际桌面验收必须使用获授权的平台账号连接并确认桌面。

2026-10-15 验收：已通过公网 `13389` 使用临时普通平台账号及平台密码完整进入目标 Windows 桌面，客户端未提供 Windows 密码；线上记录平台授权、上游桌面连接完成及约 23 秒后的断开审计，临时账号和授权已删除。正式域名证书校验通过（TLS 1.3），实际运行镜像内 46 项相关测试通过，SSH `2222` 横向检查正常。Windows 凭据已绑定资源并使用现有加密密钥保存。

该次人工验收镜像为 `frp-agent:rdp-platform-20261015-v2`，配置和数据库备份位于 `/data/compose/9/rdp-platform-20261015-v2/` 及应用数据目录中的 `rdp-platform-v2-database.before.sqlite`。后续代码更新提交 `dev` 后沿用项目自动发布流程。

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
