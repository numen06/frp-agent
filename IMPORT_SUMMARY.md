# 配置导入功能 - 完整总结

## 🎉 新增 API - 最简洁的方式

### 新 API 端点
```
POST /api/config/import/{format}/{server_id}?group_name={分组名}
```

### 使用示例

#### 基础用法
```bash
curl -u admin:admin -X POST \
  -H "Content-Type: text/plain" \
  --data-binary "@frpc.ini" \
  http://localhost:8000/api/config/import/ini/1
```

#### 指定分组
```bash
curl -u admin:admin -X POST \
  -H "Content-Type: text/plain" \
  --data-binary "@frpc.ini" \
  "http://localhost:8000/api/config/import/ini/1?group_name=production"
```

#### TOML 格式
```bash
curl -u admin:admin -X POST \
  -H "Content-Type: text/plain" \
  --data-binary "@frpc.toml" \
  http://localhost:8000/api/config/import/toml/1
```

## 📋 所有导入方式对比

| 方式 | API 端点 | 命令行数 | 依赖 | 适用场景 |
|------|----------|---------|------|---------|
| **新 API（推荐）** | `/import/{format}/{server_id}` | 4 行 | curl | ⭐️ 服务器直接执行 |
| Python 脚本 | - | 1 行 | Python | 本地使用 |
| Shell 脚本 | - | 1 行 | Bash, jq | 脚本集成 |
| JSON API | `/import/text` | 6 行 | curl, jq | 复杂场景 |
| 文件上传 | `/import` | - | - | Web 界面 |

## 🔥 新 API 的优势

1. **最简洁** - 只需 4 行命令
2. **无需 jq** - 不依赖 JSON 处理工具
3. **URL 清晰** - 参数在 URL 中一目了然
4. **统一风格** - 与 ini 转换 API 保持一致
5. **直接上传** - 使用 `--data-binary "@文件"` 直接上传

## 📦 已完成的功能

### 1. API 端点
- ✅ `/api/config/import/{format}/{server_id}` - 最简洁版（新增）
- ✅ `/api/config/import/text` - JSON 提交版
- ✅ `/api/config/import` - 文件上传版（原有）

### 2. 工具脚本
- ✅ `import_frpc_config.py` - Python 导入工具（支持 Basic Auth）
- ✅ `import_frpc_config.sh` - Shell 导入工具（支持 Basic Auth）
- ✅ `get_token.sh` - Token 获取工具

### 3. Web 界面
- ✅ 在导入配置模态框添加 curl 使用说明
- ✅ 展示最简洁的新 API 用法
- ✅ 提供复制示例和查看 Token 功能

### 4. 文档
- ✅ `CURL_SIMPLE.md` - 最简方式快速指南（新增）
- ✅ `CURL_QUICK_EXAMPLE.md` - 详细使用指南
- ✅ `README.md` - 更新主文档
- ✅ `examples/` - 示例配置文件

## 🧪 测试结果

### 测试 1: 基础导入
```bash
$ curl -u admin:admin -X POST \
  -H "Content-Type: text/plain" \
  --data-binary "@test.ini" \
  http://127.0.0.1:8000/api/config/import/ini/1

{"success":true,"message":"导入完成：新增 1 个，更新 0 个，失败 0 个",...}
```
✅ 成功

### 测试 2: 指定分组
```bash
$ curl -u admin:admin -X POST \
  -H "Content-Type: text/plain" \
  --data-binary "@test.ini" \
  "http://127.0.0.1:8000/api/config/import/ini/1?group_name=production"

{"success":true,"message":"导入完成：新增 0 个，更新 1 个，失败 0 个",...}
```
✅ 成功

### 测试 3: Python 脚本
```bash
$ ./import_frpc_config.py test.ini --username admin --password admin

✓ 导入成功
导入完成：新增 0 个，更新 1 个，失败 0 个
```
✅ 成功

### 测试 4: Shell 脚本
```bash
$ TOKEN=$(echo -n 'admin:admin' | base64)
$ ./import_frpc_config.sh test.ini $TOKEN

✓ 导入成功
导入完成：新增 0 个，更新 1 个，失败 0 个
```
✅ 成功

## 📝 API 详细说明

### 请求格式
```
POST /api/config/import/{format}/{server_id}
```

### 路径参数
- `format`: 配置格式，`ini` 或 `toml`
- `server_id`: frps 服务器 ID

### 查询参数
- `group_name`: 分组名称（可选）

### 请求头
- `Authorization`: Basic Auth（`-u username:password`）
- `Content-Type`: `text/plain`

### 请求体
配置文件的原始内容（使用 `--data-binary "@文件路径"`）

### 响应格式
```json
{
  "success": true,
  "message": "导入完成：新增 X 个，更新 Y 个，失败 Z 个",
  "stats": {
    "total": 3,
    "created": 2,
    "updated": 1,
    "failed": 0,
    "errors": []
  }
}
```

## 🎯 使用建议

### 场景 1: 服务器上快速导入
**推荐**: 使用新的简洁 API
```bash
curl -u admin:admin -X POST \
  -H "Content-Type: text/plain" \
  --data-binary "@frpc.ini" \
  http://localhost:8000/api/config/import/ini/1
```

### 场景 2: 本地脚本自动化
**推荐**: 使用 Python 或 Shell 脚本
```bash
./import_frpc_config.py frpc.ini --username admin --password admin
```

### 场景 3: CI/CD 集成
**推荐**: 使用新的简洁 API
```yaml
script:
  - curl -u $USERNAME:$PASSWORD -X POST \
      -H "Content-Type: text/plain" \
      --data-binary "@frpc.ini" \
      "$API_URL/api/config/import/ini/1"
```

### 场景 4: 批量导入
**推荐**: 循环调用新 API
```bash
for file in configs/*.ini; do
    curl -u admin:admin -X POST \
      -H "Content-Type: text/plain" \
      --data-binary "@$file" \
      http://localhost:8000/api/config/import/ini/1
done
```

## 🔗 相关文档

- [CURL_SIMPLE.md](CURL_SIMPLE.md) - 最简方式（推荐从这里开始）
- [CURL_QUICK_EXAMPLE.md](CURL_QUICK_EXAMPLE.md) - 详细示例
- [README.md](README.md) - 项目主文档
- [examples/](examples/) - 示例配置文件

## 💡 提示

1. **查看服务器 ID**: 访问 Web 界面或 `GET /api/frps-servers`
2. **查看端口使用**: `GET /api/ports/{server_id}`
3. **获取 Token**: 使用 `./get_token.sh` 脚本
4. **API 文档**: 访问 http://localhost:8000/docs

## 🎊 总结

新增的简洁 API 完美模拟了 ini 转换接口的风格：
- 简洁的 URL 格式
- 直接上传文件（`--data-binary "@文件"`）
- 参数在 URL 中清晰可见
- 无需复杂的 JSON 构建

这是目前**最简单、最直观**的配置导入方式！

