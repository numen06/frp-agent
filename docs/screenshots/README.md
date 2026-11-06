# 界面截图

截图来自 1.4.3 的生产构建，使用隔离演示数据。桌面整页截图为 1920 × 1080，关键弹窗单独取景，手机截图为 390 × 900。

| 场景 | 截图 |
| --- | --- |
| 开始使用 | [登录](login.png) · [仪表盘](dashboard.png) |
| FRP 代理 | [穿透服务](servers.png) · [内置服务](builtin-service.png) · [代理列表](proxies.png) · [分组管理](groups.png) · [生成配置](group-config.png) |
| 远程连接 | [连接服务](hosts.png) · [按主机查看](machines.png) · [Web SSH](webssh.png) · [Docker 容器](host-docker.png) · [RDP 证书校验](host-rdp.png) · [添加 VNC](vnc-add.png) · [手机键盘](vnc-mobile.png) · [连接详情](host-detail.png) |
| 权限和审计 | [凭证管理](host-credentials.png) · [访问授权](host-access.png) · [审计与流量](host-audit.png) · [连接日志](host-logs.png) · [API Key](api-keys.png) |
| 运维工具 | [运行维护](operations.png) · [安装包管理](packages.png) · [配置转换](converter.png) |

## 重拍截图

在 `frontend` 目录构建并启动预览：

```bash
npm ci
npm run build
npm run preview -- --host 127.0.0.1 --port 4173
```

在另一个终端，从仓库根目录运行：

```bash
python -m pip install playwright==1.58.0
python -m playwright install chromium
python frontend/scripts/capture_screenshots.py --screenshots-only
python frontend/scripts/check_vnc.py --docs-screenshot
python frontend/scripts/check_webssh.py --docs-screenshot
```

去掉 `--screenshots-only` 可同时检查手机布局、导航和弹窗，验证图片输出到 `data/ui-review`。脚本拦截 API 请求并阻止外部连接，截图应始终使用演示数据。
