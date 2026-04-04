#!/usr/bin/env bash
# frp-client install script
# platform: {{platform}}  version: {{version}}
set -e

FRP_DIR="/opt/frp"
FRPC_BIN="$FRP_DIR/frpc"

# --- 创建目录 ---
mkdir -p "$FRP_DIR"

# --- 下载并解压 frpc ---
echo "Downloading {{filename}} ..."
curl -sL "{{download_url}}" -o /tmp/{{filename}}
cd /tmp
tar -xzf "{{filename}}"
cp frp_*/frpc "$FRPC_BIN"
chmod 755 "$FRPC_BIN"

# --- 清理临时文件 ---
rm -f /tmp/{{filename}}
rm -rf /tmp/frp_*

# --- 配置文件（仅当不存在时下载，不覆盖已有配置）---
if [[ ! -f "$FRP_DIR/frpc.toml" ]]; then
    {{config_line}}
else
    echo "检测到已有配置文件 $FRP_DIR/frpc.toml，跳过下载以保留用户配置。"
fi

# --- 配置兼容性：frpc.ini -> frpc.toml 迁移 ---
INI_FILE="$FRP_DIR/frpc.ini"
TOML_FILE="$FRP_DIR/frpc.toml"
if [[ -f "$INI_FILE" ]]; then
    if [[ ! -f "$TOML_FILE" ]]; then
        echo "迁移到 TOML: 将 $INI_FILE 重命名为 $TOML_FILE"
        mv "$INI_FILE" "$TOML_FILE"
    else
        echo "警告: $INI_FILE 存在但 $TOML_FILE 已存在，跳过迁移以防止覆盖。"
        mv "$INI_FILE" "${INI_FILE}.backup_$(date +%Y%m%d_%H%M%S)"
    fi
fi

echo "=== Frp Client 部署完成 ==="
echo "安装路径: $FRPC_BIN"
