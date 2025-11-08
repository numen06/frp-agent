# 配置文件示例

本目录包含了 frpc 配置文件的示例，可以用于测试配置导入功能。

## 文件说明

- `frpc_example.ini` - INI 格式的配置文件示例
- `frpc_example.toml` - TOML 格式的配置文件示例

## 使用方式

### 1. 使用 Python 脚本导入

```bash
# 从项目根目录运行
cd ..

# 导入 INI 配置
./import_frpc_config.py examples/frpc_example.ini --token YOUR_TOKEN

# 导入 TOML 配置
./import_frpc_config.py examples/frpc_example.toml --token YOUR_TOKEN
```

### 2. 使用 Shell 脚本导入

```bash
# 从项目根目录运行
cd ..

# 导入 INI 配置
./import_frpc_config.sh examples/frpc_example.ini YOUR_TOKEN

# 导入 TOML 配置  
./import_frpc_config.sh examples/frpc_example.toml YOUR_TOKEN
```

### 3. 使用 curl 直接导入

```bash
# 导入 INI 配置
python3 << 'EOF'
import json
with open('examples/frpc_example.ini', 'r') as f:
    content = f.read()
data = {
    "content": content,
    "format": "ini",
    "frps_server_id": 1
}
print(json.dumps(data))
EOF | curl -X POST "http://localhost:8000/api/config/import/text" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d @-
```

## 注意事项

1. 这些示例文件中的端口号仅供参考，导入前请确认端口没有被占用
2. 导入配置前，请确保已经在系统中添加了对应的 frps 服务器
3. 示例中的 `server_addr`、`token` 等连接信息仅为示例，实际使用时会被系统中配置的服务器信息覆盖
4. 分组名称会从代理名称中自动解析（如 `prod_api` 会被归入 `prod` 分组）

## 自定义配置

你可以根据这些示例创建自己的配置文件：

1. 复制示例文件
2. 修改代理名称、端口号等参数
3. 使用导入工具导入到系统中

