#!/usr/bin/env bash
# frp-client upgrade script
# platform: {{platform}}  version: {{version}}
set -e

FRP_DIR="{{install_path}}"
FRPC_BIN="$FRP_DIR/frpc"

# --- 检查是否已安装 ---
if [[ ! -f "$FRPC_BIN" ]]; then
    echo "错误: 未检测到已安装的 frpc ($FRPC_BIN)，请先使用安装脚本进行安装。"
    exit 1
fi

OLD_VERSION=$("$FRPC_BIN" --version 2>&1 || true)
echo "当前版本: $OLD_VERSION"
echo "目标版本: {{version}}"

# --- 停止 frpc 服务（如已注册为 systemd 服务）---
if command -v systemctl &>/dev/null && systemctl is-active --quiet frpc 2>/dev/null; then
    echo "停止 frpc 服务..."
    systemctl stop frpc
fi

# --- 备份当前 frpc ---
if [[ -f "$FRPC_BIN" ]]; then
    BACKUP="$FRP_DIR/frpc.bak"
    cp "$FRPC_BIN" "$BACKUP"
    echo "已备份当前版本: $BACKUP"
fi

# --- 下载并替换 ---
echo "下载 {{filename}} ..."
curl -sL "{{download_url}}" -o /tmp/{{filename}}
cd /tmp
tar -xzf "{{filename}}"
cp frp_*/frpc "$FRPC_BIN"
chmod 755 "$FRPC_BIN"

# --- 清理临时文件 ---
rm -f /tmp/{{filename}}
rm -rf /tmp/frp_*

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

# --- 重启 frpc 服务 ---
if command -v systemctl &>/dev/null && systemctl is-enabled --quiet frpc 2>/dev/null; then
    echo "启动 frpc 服务..."
    systemctl start frpc
fi

NEW_VERSION=$("$FRPC_BIN" --version 2>&1 || true)
echo "=== Frp Client 升级完成 ==="
echo "版本: $OLD_VERSION -> $NEW_VERSION"
echo "安装路径: $FRPC_BIN"
