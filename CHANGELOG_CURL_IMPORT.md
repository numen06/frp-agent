# 更新日志 - CURL 导入功能

## 版本: 1.1.0
**发布日期**: 2025-11-08

### 新增功能

#### 📦 配置文件 curl 导入支持

添加了通过 curl 和 API 直接导入 frpc 配置文件的功能，支持 INI 和 TOML 两种格式。

**核心特性**:

1. **新增 API 端点** (`POST /api/config/import/text`)
   - 支持通过 JSON body 提交配置文件内容
   - 支持 INI 和 TOML 格式
   - 自动端口冲突检测
   - 自动分组识别
   - 完整的错误处理和统计

2. **便捷工具脚本**:
   - `import_frpc_config.py` - Python 版本的导入工具
     - 支持 token 和用户名密码认证
     - 自动检测配置格式
     - 美化的输出结果
     - 完整的错误处理
   
   - `import_frpc_config.sh` - Shell 版本的导入工具
     - 纯 Shell + curl 实现
     - 适合在 CI/CD 中使用
     - 彩色输出
     - 环境变量支持

3. **详细文档**:
   - `CURL_IMPORT_GUIDE.md` - 完整的使用指南
     - curl 命令示例
     - 工具脚本使用说明
     - CI/CD 集成示例
     - 故障排除指南
   
   - `examples/` - 示例配置文件目录
     - `frpc_example.ini` - INI 格式示例
     - `frpc_example.toml` - TOML 格式示例
     - `README.md` - 示例使用说明

4. **测试工具**:
   - `test_import.py` - 自动化测试脚本
     - 测试 INI 和 TOML 格式导入
     - 测试错误处理
     - 测试认证机制

### 改进的文件

#### `app/routers/config_import.py`
- 新增 `ConfigImportRequest` Pydantic 模型
- 新增 `import_config_text()` API 端点
- 添加详细的 docstring 和使用示例

#### `README.md`
- 在功能特性中添加配置导入说明
- 添加 curl 导入快速开始指南
- 添加工具脚本使用说明
- 添加新的 API 端点文档

### 使用示例

#### 使用 Python 脚本导入

```bash
# 最简单的方式
./import_frpc_config.py frpc.ini --token YOUR_TOKEN

# 使用用户名密码
./import_frpc_config.py frpc.ini --username admin --password secret

# 指定服务器和分组
./import_frpc_config.py frpc.toml --token YOUR_TOKEN --server-id 2 --group production
```

#### 使用 Shell 脚本导入

```bash
./import_frpc_config.sh frpc.ini YOUR_TOKEN 1 ini default
```

#### 使用原生 curl

```bash
curl -X POST "http://localhost:8000/api/config/import/text" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "[ssh]\ntype = tcp\nlocal_ip = 127.0.0.1\nlocal_port = 22\nremote_port = 6000",
    "format": "ini",
    "frps_server_id": 1
  }'
```

### API 变更

#### 新增端点

```
POST /api/config/import/text
```

**请求体**:
```json
{
  "content": "配置文件内容",
  "format": "ini",  // 或 "toml"
  "frps_server_id": 1,
  "group_name": "default"  // 可选
}
```

**响应**:
```json
{
  "success": true,
  "message": "导入完成：新增 2 个，更新 1 个，失败 0 个",
  "stats": {
    "total": 3,
    "created": 2,
    "updated": 1,
    "failed": 0,
    "errors": []
  }
}
```

### 技术细节

- **认证**: 使用 Bearer Token 认证
- **格式支持**: INI 和 TOML
- **端口管理**: 自动检测端口冲突并分配
- **分组识别**: 从代理名称自动解析分组（如 `prod_api` → `prod` 分组）
- **覆盖更新**: 同名代理（相同 name + frps_server_id）会被完全覆盖
- **错误处理**: 单个代理失败不影响其他代理的导入

### 兼容性

- **向后兼容**: 保留了原有的文件上传接口 `POST /api/config/import`
- **Python 版本**: 需要 Python 3.6+
- **Shell 版本**: 需要 bash 和 jq
- **依赖**: requests 库（仅 Python 工具需要）

### 测试

运行测试脚本验证功能：

```bash
# 确保服务器正在运行
python app.py

# 在另一个终端运行测试
python test_import.py
```

### 使用场景

1. **批量迁移**: 快速导入现有的 frpc 配置文件
2. **自动化部署**: 在 CI/CD 管道中自动同步配置
3. **配置备份**: 定期导出和导入配置
4. **多环境管理**: 在不同环境间快速同步配置
5. **脚本集成**: 在自动化脚本中调用 API

### 注意事项

1. 需要有效的认证 token
2. 确保目标 frps 服务器已在系统中配置
3. 导入前检查端口是否可用
4. 同名代理会被完全覆盖（按 name + frps_server_id 判断）
5. 配置文件必须是有效的 UTF-8 编码

### 后续计划

- [ ] 添加批量导入多个配置文件的支持
- [ ] 添加配置文件验证和预览功能
- [ ] 支持从 URL 直接导入配置
- [ ] 添加配置文件模板功能
- [ ] 支持配置文件的差异对比

### 相关文档

- [CURL 导入完整指南](CURL_IMPORT_GUIDE.md)
- [示例配置文件](examples/)
- [主 README](README.md)
- [API 文档](http://localhost:8000/docs) (启动服务后访问)

### 贡献者

- 开发: AI Assistant
- 测试: -
- 文档: AI Assistant

---

如有问题或建议，请提交 Issue 或 Pull Request。

