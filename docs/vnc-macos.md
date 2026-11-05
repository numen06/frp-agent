# macOS VNC 纳管

VNC 主机沿用主机列表、管理员编辑、`connect` 授权、有效期、连接测试、日志与流量统计。授权用户在主机卡片或详情中进入“远程桌面”，使用浏览器连接；此次没有新增公网原生 VNC 监听端口。

## 配置

1. 在 Mac 开启“远程登录”（SSH）与“屏幕共享”，在屏幕共享设置中允许 VNC 显示器使用密码控制屏幕。此版本支持传统 VNC 密码认证，不支持仅 Apple ARD 账号认证的配置。
2. 把该 Mac 的 SSH 服务纳入平台管理，配置独立、最小权限的 SSH 账号，执行连接测试并通过可信渠道核验 SSH 主机指纹。SSH 服务需要允许 `direct-tcpip` 转发到本机 VNC 端口；可使用 `PermitOpen 127.0.0.1:5900` 限制转发目标。若通过 FRP 接入，只需转发 SSH，禁止向公网暴露 5900。
3. 添加 VNC 主机，地址填 `127.0.0.1`、端口通常 `5900`，选择对应 Mac SSH 主机。绑定专用 VNC 密码凭据；用户名填 `vnc` 用作标识。传统 VNC 仅支持前 8 字节密码，因此平台拒绝超过 8 位或非 ASCII 的密码，避免静默截断。
4. 运行连接测试，再为用户授予该 VNC 主机的连接权限。无需授予 SSH 执行权限；平台只允许该桌面通过所选 SSH 主机访问其回环地址。
5. 通过平台 HTTPS 地址打开远程桌面并点击“连接桌面”。使用支持 ES2022 的现代浏览器。

## 保护与部署

- 浏览器到平台强制 HTTPS/WSS，并检查 Origin 与 Host 相同；禁止在 WebSocket URL 携带参数或认证信息，登录凭据只在首条认证消息中提交。
- 平台到 Mac 使用 SSH 加密通道，必须有已登记的 SSH 指纹；指纹不一致立即拒绝。VNC 密码使用现有 AES-GCM 凭据存储，仅由服务端完成挑战认证，不向浏览器返回密码或挑战响应。不接受目标的无密码认证。
- SSH 转发目的地固定为 `127.0.0.1`；VNC 主机只能由管理员创建或修改，客户端不能指定目标地址。
- 每个进程最多 16 个活动 VNC 会话、每个账号最多 2 个，最多 32 个待认证连接。认证/协议握手有超时，单条输入限制 64 KiB，会话最长 1 小时。每 5 秒复核账号、授权有效期、主机启用状态、指纹及凭据变化，撤销后自动断开。多个工作进程会分别计数，建议沿用单 worker 部署。
- 审计记录连接、结束、失败、时长和平台到目标方向的流量，不记录桌面内容、键盘输入或密码；连接测试不代表用户已经看到桌面。
- 当前空闲检测按客户端 RFB 数据计时，客户端自动轮询也会刷新计时；最长 1 小时仍强制结束。
- 生产环境设置独立的 `SSH_CREDENTIAL_SECRET`，不要使用开发派生密钥。Mac 防火墙应限制 VNC 仅供受信任的本机/局域网来源，SSH 只对平台出口或受保护隧道开放。

TLS 在反向代理终止时，代理应转发 WebSocket Upgrade、原始 Host（含非标准端口）及 `X-Forwarded-Proto: https`。Uvicorn 只信任受控代理 IP 的转发头，例如 `--proxy-headers --forwarded-allow-ips=<代理IP>`。不要为不受信任的外部来源开启任意转发头信任。内置前端 nginx 已支持 Upgrade；若另套 HTTPS 入口，请在 TLS 终止处正确设置协议头，否则 WSS 会被拒绝。

数据库启动迁移会增加可空的 `vnc_ssh_host_id` 字段；已有主机数据保持兼容。被 VNC 使用的 SSH 主机不能删除，需先调整关联关系。主服务和可选 Web SSH worker 均注册 VNC WebSocket 路由。

## 隔离容器验收

可使用 `backend/scripts/check_vnc_live.py` 验证完整链路。它启动临时 HTTPS 应用、真实 SSH 服务和受密码保护的 RFB 测试服务，验证平台 CRUD、WSS 桌面帧、越权拦截、授权撤销、密码与指纹错误拦截及审计脱敏。测试目标是协议夹具，不是真实 Mac。

在 NUC 的测试镜像上运行（以下口令仅用于无网络、无数据卷的临时测试）：

```sh
docker -H tcp://192.168.8.119:2375 run --rm --network none \
  --memory 512m --cpus 1 --pids-limit 128 \
  -e VNC_DISPOSABLE_TEST=1 -e DATABASE_URL=sqlite:////tmp/vnc-live.db \
  -e AUTH_USERNAME=vnc-test-admin -e AUTH_PASSWORD=isolated-test-only \
  -e SSH_CREDENTIAL_SECRET=isolated-test-key-only \
  -e SSH_GATEWAY_ENABLED=false -e DOCKER_GATEWAY_ENABLED=false -e RDP_GATEWAY_ENABLED=false \
  -e PYTHONPATH=/app/backend --entrypoint python \
  frp-agent:vnc-nuc-20261105 /app/backend/scripts/check_vnc_live.py
```

该命令不挂载宿主数据、不发布端口，全部服务在容器回环地址通信；不要将测试数据库指向真实部署。
