# curl 导入配置 - 最简单的方式

## 一行命令完成导入！

```bash
curl -u admin:admin -X POST \
  -H "Content-Type: text/plain" \
  --data-binary "@frpc.ini" \
  http://localhost:8000/api/config/import/ini/test_server/production
```

就这么简单！✨

## URL 格式说明

```
http://localhost:8000/api/config/import/{格式}/{服务器名称}/{分组名称}
                                         ↓        ↓           ↓
                                      ini/toml  服务器名    分组名
```

## 完整示例

### 1. 导入 INI 配置到 test_server 的 production 分组

```bash
curl -u admin:admin -X POST \
  -H "Content-Type: text/plain" \
  --data-binary "@frpc.ini" \
  http://localhost:8000/api/config/import/ini/test_server/production
```

### 2. 导入 TOML 配置到 prod_server 的 default 分组

```bash
curl -u admin:admin -X POST \
  -H "Content-Type: text/plain" \
  --data-binary "@frpc.toml" \
  http://localhost:8000/api/config/import/toml/prod_server/default
```

### 3. 导入到 dev_server 的 testing 分组

```bash
curl -u admin:admin -X POST \
  -H "Content-Type: text/plain" \
  --data-binary "@frpc.ini" \
  http://localhost:8000/api/config/import/ini/dev_server/testing
```

### 4. 使用变量批量导入

```bash
#!/bin/bash

API_URL="http://localhost:8000"
USERNAME="admin"
PASSWORD="admin"
SERVER_NAME="test_server"
GROUP_NAME="production"

for file in configs/*.ini; do
    echo "导入: $file"
    curl -u "$USERNAME:$PASSWORD" -X POST \
      -H "Content-Type: text/plain" \
      --data-binary "@$file" \
      "$API_URL/api/config/import/ini/$SERVER_NAME/$GROUP_NAME"
    echo
done
```

## 成功返回示例

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

## 与其他方式对比

| 方式 | 命令长度 | 依赖 | 复杂度 |
|------|---------|------|-------|
| **新 API（推荐）** | 4 行 | curl | ⭐️ |
| 项目脚本 | 1 行 | Python/Shell | ⭐️⭐️ |
| JSON API | 6 行 | curl + jq | ⭐️⭐️⭐️ |

## 优势

✅ **最简洁** - 只需 4 行命令  
✅ **无需 jq** - 不依赖 JSON 处理工具  
✅ **URL 清晰** - 格式和服务器 ID 在 URL 中一目了然  
✅ **与转换 API 一致** - 使用相同的风格（`--data-binary "@文件"`）  

## 参数说明

- **认证**: `-u admin:admin` 或 `-u username:password`
- **格式**: URL 中的 `ini` 或 `toml`
- **服务器 ID**: URL 末尾的数字
- **分组**: 查询参数 `?group_name=xxx`（可选）
- **文件**: `--data-binary "@文件路径"`

## 常见问题

### Q: 如何查看我的服务器 ID？
A: 访问 Web 界面查看，或使用 API：
```bash
curl -u admin:admin http://localhost:8000/api/frps-servers | jq .
```

### Q: 可以同时导入多个文件吗？
A: 可以用脚本循环导入：
```bash
for file in *.ini; do
    curl -u admin:admin -X POST \
      -H "Content-Type: text/plain" \
      --data-binary "@$file" \
      http://localhost:8000/api/config/import/ini/1
done
```

### Q: 支持从标准输入读取吗？
A: 支持！去掉 `@` 符号：
```bash
cat frpc.ini | curl -u admin:admin -X POST \
  -H "Content-Type: text/plain" \
  --data-binary @- \
  http://localhost:8000/api/config/import/ini/1
```

## 更多信息

- 完整 API 文档：http://localhost:8000/docs
- 其他导入方式：查看 `CURL_QUICK_EXAMPLE.md`
- 项目文档：`README.md`

