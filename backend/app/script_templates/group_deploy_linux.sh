#!/usr/bin/env bash
# frp-client deploy script (install / optional upgrade / optional config overwrite + systemd)
# platform: {{platform}}  version: {{version}}
set -e

FRP_DIR="{{install_path}}"
FRPC_BIN="$FRP_DIR/frpc"
CONFIG_FILE="$FRP_DIR/frpc.toml"
UPGRADE="{{upgrade}}"
FORCE_CONFIG="{{force_config}}"

# ── 0. root 检测（systemd 需要）────────────────────────
IS_ROOT=false
if [ "$(id -u)" -eq 0 ]; then
    IS_ROOT=true
else
    echo "提示: 未以 root 运行。将仅安装文件到 $FRP_DIR，不会注册 systemd；请手动以 root 执行或: sudo bash"
fi

# ── 1. 检测当前状态 ──────────────────────────────────
INSTALLED=false
if [ -f "$FRPC_BIN" ]; then
    INSTALLED=true
    CURRENT_VERSION=$("$FRPC_BIN" --version 2>&1 || echo "unknown")
    echo "当前已安装: $CURRENT_VERSION"
else
    echo "未检测到已安装的 frpc，将执行全新安装。"
fi

# ── 2. 下载 frpc 二进制 ─────────────────────────────
DO_DOWNLOAD=false
if [ "$INSTALLED" = "false" ]; then
    DO_DOWNLOAD=true
    echo "首次安装，需要下载 frpc 二进制。"
elif [ "$UPGRADE" = "true" ]; then
    DO_DOWNLOAD=true
    echo "已启用升级，将下载并替换 frpc 二进制。"
else
    echo "已安装且未启用升级，跳过二进制下载。"
fi

if [ "$DO_DOWNLOAD" = "true" ]; then
    if [ "$INSTALLED" = "true" ] && [ "$IS_ROOT" = "true" ] && command -v systemctl &>/dev/null; then
        if systemctl is-active --quiet frpc 2>/dev/null; then
            echo "停止 frpc 服务以便替换二进制..."
            systemctl stop frpc || true
        fi
    fi
    echo "正在下载 {{filename}} ..."
    mkdir -p "$FRP_DIR"
    cd /tmp
    curl -fSL -o "{{filename}}" "{{download_url}}" \
      && tar -xzf "{{filename}}" \
      && cp -f frp_*/frpc "$FRP_DIR/"
    chmod 755 "$FRPC_BIN"
    rm -f "{{filename}}"
    rm -rf frp_*
    NEW_VERSION=$("$FRPC_BIN" --version 2>&1 || echo "unknown")
    echo "frpc 二进制已就绪: $NEW_VERSION"
fi

# ── 3. 处理配置文件 ─────────────────────────────────
DO_CONFIG=false
if [ "$INSTALLED" = "false" ]; then
    DO_CONFIG=true
    echo "首次安装，需要下载配置文件。"
elif [ "$FORCE_CONFIG" = "true" ]; then
    DO_CONFIG=true
    echo "已启用覆盖配置，将重新下载配置文件。"
elif [ ! -f "$CONFIG_FILE" ]; then
    DO_CONFIG=true
    echo "配置文件不存在，将下载配置。"
else
    echo "配置文件已存在且未启用覆盖，跳过配置下载。"
fi

if [ "$DO_CONFIG" = "true" ]; then
    mkdir -p "$FRP_DIR"
    echo "正在下载配置文件 ..."
    curl -sL "{{config_url}}" -o "$CONFIG_FILE"
    echo "配置文件已保存: $CONFIG_FILE"
fi

# ── 4. frpc.ini -> frpc.toml 迁移 ───────────────────
INI_FILE="$FRP_DIR/frpc.ini"
if [ -f "$INI_FILE" ]; then
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "迁移到 TOML: 将 $INI_FILE 重命名为 $CONFIG_FILE"
        mv "$INI_FILE" "$CONFIG_FILE"
    else
        echo "警告: $INI_FILE 存在但 $CONFIG_FILE 已存在，备份旧 ini。"
        mv "$INI_FILE" "${INI_FILE}.backup_$(date +%Y%m%d_%H%M%S)"
    fi
fi

# ── 5. systemd 服务 ─────────────────────────────────
SERVICE_FILE="/etc/systemd/system/frpc.service"
if [ "$IS_ROOT" = "true" ] && command -v systemctl &>/dev/null; then
    if [ ! -f "$SERVICE_FILE" ]; then
        echo "注册 systemd 服务: $SERVICE_FILE"
        cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=frp client service
After=network.target

[Service]
Type=simple
Restart=on-failure
RestartSec=5s
ExecStart=$FRPC_BIN -c $CONFIG_FILE
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
EOF
        systemctl daemon-reload
        systemctl enable frpc
        echo "systemd 服务已注册并启用开机自启。"
    else
        echo "systemd 服务文件已存在: $SERVICE_FILE"
    fi

    echo "启动 / 重启 frpc 服务 ..."
    systemctl restart frpc || systemctl start frpc
else
    echo "未注册 systemd。可手动运行: $FRPC_BIN -c $CONFIG_FILE"
fi

# ── 6. 完成 ─────────────────────────────────────────
FINAL_VERSION=$("$FRPC_BIN" --version 2>&1 || echo "unknown")
echo ""
echo "========================================="
echo "  frpc 部署完成"
echo "  版本: $FINAL_VERSION"
echo "  路径: $FRPC_BIN"
echo "  配置: $CONFIG_FILE"
echo "========================================="
