# 列表分页与维护

所有管理列表默认每页 20 条，上限 100 条。搜索和权限过滤在分页前执行，删除末页最后一条记录后会自动回到有效页。

| 数据 | 处理方式 |
| --- | --- |
| FRP 服务器、代理、分组、分组内代理 | SQL 计数与 LIMIT / OFFSET；服务器统计与全局汇总独立计算 |
| 主机、访问授权、用户 / API Key 授权对象 | SQL 分页，先应用权限与筛选 |
| SSH / Docker 凭据、API Key、安装包 | SQL 分页；远程选择器支持搜索、翻页及已选项回显 |
| 端口分配、同步历史、访问审计 | SQL 分页；审计另提供单条详情和管理员维护接口 |
| Docker 容器 | 从 Docker / Portainer 获取后排序分页；上游接口仍返回完整容器列表 |
| 客户端升级结果 | 对已保存的任务 JSON 分页返回；服务端仍需解析该任务的完整 JSON |
| 本次上传文件、导入结果 | 对当前操作的有限本地结果分页展示 |

导航、固定枚举、平台 / 版本目录和汇总数字不属于记录列表，不进行分页。完整配置下载与后台同步操作继续处理整个目标范围，不受界面页码限制。

## API 约定

新客户端应传入 `page=1&page_size=20`，读取 `{items,total,page,page_size}`。`page` 从 1 开始，`page_size` 范围 1–100；超出范围返回 422。集合支持的筛选参数随各接口定义。

此前返回数组的服务器、凭据、API Key、主机、授权对象、授权记录、审计接口，在不传 `page` 时仍返回数组，但默认最多 20 条。依赖旧版全量数组的自动化调用必须改为逐页读取；不能再假定一次请求返回全部记录。

分组名称接口同时保留 `groups`，容器接口同时保留 `containers`，其内容均为当前页。代理、分组、安装包等原有分页接口统一默认 20 条。

## 审计维护

- `GET /api/managed-hosts/audit/logs`：分页与主机、动作、结果、关键词、开始 / 结束时间筛选。
- `GET /api/managed-hosts/audit/logs/{id}`：完整详情，沿用列表的身份隔离。
- `POST /api/managed-hosts/audit/delete`：管理员删除指定 `ids`，单次最多 100 条。
- `POST /api/managed-hosts/audit/cleanup`：管理员按 `keep_days`（1–3650）和可选 `host_id` 清理；`dry_run` 默认为 `true`，先返回预览数量。

每次实际删除会为受影响主机保留新的维护审计记录。界面在确认前不会执行删除。

## 分组生命周期

创建时可通过 `create_defaults=true` 同时生成三个标准代理，分组、代理与端口分配在一个事务内完成。失败时整体回滚。

非空分组删除需要 `delete_proxies=true` 与预览时的 `expected_proxy_count`；数量变化时返回 409，必须重新查看并确认。删除清除该组代理与 SSH 状态、释放已分配端口，并保留已完成任务历史；运行中的扫描 / 升级任务会阻止删除。此操作不会停止远端正在运行的 frpc，需要重新交付配置或停止对应客户端。

## 回归验证

后端：`python -m pytest backend/tests -q`。

前端构建后，在 `127.0.0.1:4173` 启动 Vite preview，运行 `frontend/scripts/check_list_interactions.py` 和 `frontend/scripts/capture_screenshots.py`。两个脚本均拦截接口并使用虚构演示数据，不访问生产数据。
