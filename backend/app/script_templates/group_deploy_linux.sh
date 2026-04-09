#!/usr/bin/env bash
# frp-client deploy script (install / optional upgrade / optional config overwrite + systemd)
# platform: {{platform}}  version: {{version}}
# 配置策略：先迁移 frpc.ini，再决定是否从平台拉取 frpc.toml；覆盖前自动带时间戳备份。
set -e

FRP_DIR="{{install_path}}"
FRPC_BIN="$FRP_DIR/frpc"
CONFIG_FILE="$FRP_DIR/frpc.toml"
INI_FILE="$FRP_DIR/frpc.ini"
UPGRADE="{{upgrade}}"
FORCE_CONFIG="{{force_config}}"

# 若文件存在则复制一份带时间戳的备份（不删除原文件）
backup_copy() {
    local f="$1"
    [ -f "$f" ] || return 0
    local bak="${f}.backup_$(date +%Y%m%d_%H%M%S)"
    cp "$f" "$bak"
    echo "已备份: $f -> $bak"
}

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

mkdir -p "$FRP_DIR"

# ── 3. frpc.ini 迁移（必须在拉取 frpc.toml 之前）──────
if [ -f "$INI_FILE" ]; then
    if [ ! -f "$CONFIG_FILE" ]; then
        backup_copy "$INI_FILE"
        echo "迁移 INI -> TOML: $INI_FILE -> $CONFIG_FILE"
        mv "$INI_FILE" "$CONFIG_FILE"
    else
        echo "检测到 frpc.ini 与 frpc.toml 并存，不合并内容；将 ini 备份移走（保留现有 toml）。"
        backup_copy "$INI_FILE"
        mv "$INI_FILE" "${INI_FILE}.backup_$(date +%Y%m%d_%H%M%S)"
    fi
fi

# ── 4. 是否从平台拉取配置（迁移完成后根据当前文件判断）──
# 规则：无 frpc.toml 时必须拉取；已有 toml 时仅 force_config=true 才覆盖（含迁移得到的 toml）。
DO_CONFIG=false
if [ "$FORCE_CONFIG" = "true" ]; then
    DO_CONFIG=true
    echo "已启用覆盖配置，将从平台重新下载 frpc.toml。"
elif [ ! -f "$CONFIG_FILE" ]; then
    DO_CONFIG=true
    echo "未找到 frpc.toml，将从平台下载配置。"
else
    echo "已存在 frpc.toml 且未启用覆盖，跳过从平台下载配置。"
fi

if [ "$DO_CONFIG" = "true" ]; then
    if [ -f "$CONFIG_FILE" ]; then
        backup_copy "$CONFIG_FILE"
    fi
    TMP="${CONFIG_FILE}.tmp.$$"
    rm -f "$TMP"
    echo "正在下载配置文件 ..."
    if ! curl -fsSL "{{config_url}}" -o "$TMP"; then
        rm -f "$TMP"
        echo "错误: 下载配置失败（请检查网络与 API）。" >&2
        exit 1
    fi
    mv -f "$TMP" "$CONFIG_FILE"
    echo "配置文件已保存: $CONFIG_FILE"
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
