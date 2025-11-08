# 系统更新说明

## 🎉 版本更新 - 2025-11-08

### 核心功能重构

#### 1. 移除"同步状态"概念
- ✅ 代理列表直接从 frps 服务器实时拉取
- ✅ 与本地数据库进行对比分析
- ✅ **本地数据库作为主数据源**（最全的记录）
- ✅ frps 可能会丢失数据，本地数据库保持完整

#### 2. 添加分组管理功能
- ✅ 自动从代理名称解析分组（如 `dlyy_rdp` → 分组 `dlyy`）
- ✅ 支持按分组过滤代理列表
- ✅ 支持按在线/离线状态过滤
- ✅ 实时显示过滤统计

#### 3. UI/UX 改进
- ✅ 移除"同步状态"按钮
- ✅ 移除"添加代理"功能（代理由 frpc 自动注册）
- ✅ 添加分组过滤下拉框
- ✅ 添加状态过滤下拉框
- ✅ 添加"刷新"按钮
- ✅ 实时显示对比分析结果

#### 4. 代理列表增强
- ✅ 显示分组列
- ✅ 显示过滤结果统计
- ✅ 优化表格布局
- ✅ 移除删除操作（代理应从 frpc 端管理）

#### 5. 数据对比分析
- ✅ 实时对比本地和 frps 数据
- ✅ 显示在线代理数量
- ✅ 显示状态变更
- ✅ 显示 frps 中缺失的代理（可能丢失）
- ✅ 显示新发现的代理

### 新增 API 接口

#### 分组管理 API
```bash
# 获取分组列表及统计
GET /api/groups?frps_server_id={id}

# 获取分组的所有代理
GET /api/groups/{group_name}/proxies?frps_server_id={id}

# 获取分组详细统计
GET /api/groups/{group_name}/summary?frps_server_id={id}
```

#### frpc 配置生成 API
```bash
# 根据分组生成配置
GET /api/frpc/config/by-group/{group_name}?frps_server_id={id}

# 生成一键安装脚本
GET /api/frpc/install-script/by-group/{group_name}?frps_server_id={id}

# 根据代理ID列表生成配置
POST /api/frpc/config/by-proxies
```

#### 代理列表 API（更新）
```bash
# 获取代理列表，支持实时对比
GET /api/proxies?frps_server_id={id}&group_name={group}&status={status}&sync_from_frps=true

返回格式:
{
  "proxies": [...],  // 代理列表
  "analysis": {      // 对比分析结果
    "total_in_db": 100,
    "total_in_frps": 98,
    "online_proxies": [...],
    "missing_in_frps": [...],
    "only_in_frps": [...],
    "status_changed": [...]
  }
}
```

#### 数据分析 API（原同步接口）
```bash
# 对比分析本地和frps数据
POST /api/analysis/compare?frps_server_id={id}&auto_update=true

# 获取分析历史
GET /api/analysis/history?frps_server_id={id}&limit=50
```

### 使用示例

#### 1. 按分组生成配置并安装

```bash
# 查看所有分组
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://your-server:8000/api/groups?frps_server_id=1"

# 生成分组配置
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://your-server:8000/api/frpc/config/by-group/dlyy?frps_server_id=1" \
  > frpc_dlyy.ini

# 获取一键安装脚本
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://your-server:8000/api/frpc/install-script/by-group/dlyy?frps_server_id=1" \
  > install.sh

chmod +x install.sh
sudo ./install.sh
```

#### 2. 查看对比分析

```bash
# 获取代理列表并对比
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://your-server:8000/api/proxies?frps_server_id=1&sync_from_frps=true"
```

### 数据库迁移

执行以下命令添加 `group_name` 字段：

```bash
cd /path/to/frp-agent
source venv/bin/activate
python app/migrations/add_proxy_group_name.py
```

### 依赖更新

- ✅ 修复 `bcrypt` 版本兼容性（降级到 3.2.0）
- ✅ 添加 `pyyaml` 支持

### 升级注意事项

1. **数据库迁移**: 必须先运行迁移脚本
2. **清除浏览器缓存**: 前端有较大改动
3. **配置兼容**: 现有配置完全兼容
4. **API 兼容**: 旧的 API 接口保持兼容

### 系统架构说明

```
┌─────────────────────────────────────────────────┐
│                   前端 UI                        │
│   - 分组过滤                                     │
│   - 状态过滤                                     │
│   - 实时刷新                                     │
│   - 对比分析展示                                 │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│              本地数据库 (SQLite)                  │
│         📊 主数据源 - 完整记录                    │
│   - 代理列表                                     │
│   - 分组信息                                     │
│   - 历史记录                                     │
└─────────────────┬───────────────────────────────┘
                  │ 对比分析
┌─────────────────▼───────────────────────────────┐
│              frps 服务器                          │
│         ☁️ 运行时状态                            │
│   - 在线代理                                     │
│   - 实时流量                                     │
│   - 可能丢失历史数据                             │
└─────────────────────────────────────────────────┘
```

### 工作流程

1. **用户访问**: 查看代理列表
2. **自动拉取**: 从 frps 获取最新数据
3. **对比分析**: 与本地数据库对比
4. **展示结果**: 显示差异和分析
5. **分组管理**: 根据代理名称自动分组
6. **配置生成**: 按分组生成 frpc 配置

---

## 技术支持

如有问题，请查看日志或提交 Issue。

