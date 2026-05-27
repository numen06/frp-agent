#!/usr/bin/env bash
# frp-client deploy script (install / optional upgrade / optional config overwrite + systemd)
# platform: {{platform}}  version: {{version}}
# 配置策略：先迁移 frpc.ini，再决定是否从平台拉取 frpc.toml；覆盖前自动带时间戳备份。
# 可选：部署后轮询 frp-agent deploy-verify，失败则回退二进制与 toml 备份。
set -e

FRP_DIR="{{install_path}}"
FRPC_BIN="$FRP_DIR/frpc"
CONFIG_FILE="$FRP_DIR/frpc.toml"
INI_FILE="$FRP_DIR/frpc.ini"
UPGRADE="{{upgrade}}"
FORCE_CONFIG="{{force_config}}"
VERIFY_ENABLED="{{verify_enabled}}"
VERIFY_URL='{{verify_url}}'

ROLLBACK_FRPC_AVAILABLE=0
ROLLBACK_TOML_BAK=""

# 若文件存在则复制一份带时间戳的备份（不删除原文件）
backup_copy() {
    local f="$1"
    [ -f "$f" ] || return 0
    local bak="${f}.backup_$(date +%Y%m%d_%H%M%S)"
    cp "$f" "$bak"
    echo "已备份: $f -> $bak"
}

# 覆盖 frpc.toml 前备份，并记录路径供校验失败时回退（勿用于 ini 迁移）
backup_toml_for_rollback() {
    [ -f "$CONFIG_FILE" ] || return 0
    local bak="${CONFIG_FILE}.backup_$(date +%Y%m%d_%H%M%S)"
    cp "$CONFIG_FILE" "$bak"
    ROLLBACK_TOML_BAK="$bak"
    echo "已备份 frpc.toml（校验失败可回退）: $bak"
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
    if [ "$INSTALLED" = "true" ] && [ -f "$FRPC_BIN" ]; then
        cp "$FRPC_BIN" "$FRP_DIR/frpc.bak.deploy"
        ROLLBACK_FRPC_AVAILABLE=1
        echo "已备份当前 frpc 二进制 -> $FRP_DIR/frpc.bak.deploy"
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
        echo "检测到旧 INI 配置，已备份；将从平台拉取新的 frpc.toml，避免 INI 被 TOML 解析导致启动失败。"
        mv "$INI_FILE" "${INI_FILE}.backup_$(date +%Y%m%d_%H%M%S)"
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
        backup_toml_for_rollback
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

# ── 6. 部署后校验与回退（可选）────────────────────────
if [ "$VERIFY_ENABLED" = "true" ]; then
    if ! command -v python3 &>/dev/null; then
        echo "警告: 未找到 python3，跳过部署后代理校验（建议安装 python3，或生成脚本时使用 verify=false）。"
    else
        set +e
        attempt=0
        verify_ok=0
        max_attempt={{verify_attempts}}
        while [ "$attempt" -lt "$max_attempt" ]; do
            json=$(curl -fsS "$VERIFY_URL" 2>/dev/null)
            if [ $? -eq 0 ] && echo "$json" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('sync_ok') and d.get('ok') else 1)" 2>/dev/null; then
                verify_ok=1
                echo "部署校验通过（online 需 >= {{min_online}}，详见 frp-agent deploy-verify）。"
                break
            fi
            attempt=$((attempt + 1))
            if [ "$attempt" -lt "$max_attempt" ]; then
                sleep {{verify_interval}}
            fi
        done
        set -e
        if [ "$verify_ok" -ne 1 ]; then
            echo "部署校验未通过或无法拉取校验接口；尝试回退已备份的二进制/配置..." >&2
            if [ "$IS_ROOT" = "true" ] && command -v systemctl &>/dev/null; then
                systemctl stop frpc 2>/dev/null || true
                if [ "$ROLLBACK_FRPC_AVAILABLE" = "1" ] && [ -f "$FRP_DIR/frpc.bak.deploy" ]; then
                    cp -f "$FRP_DIR/frpc.bak.deploy" "$FRPC_BIN"
                    chmod 755 "$FRPC_BIN"
                    echo "已回退 frpc 二进制。"
                fi
                if [ -n "$ROLLBACK_TOML_BAK" ] && [ -f "$ROLLBACK_TOML_BAK" ]; then
                    cp -f "$ROLLBACK_TOML_BAK" "$CONFIG_FILE"
                    echo "已回退 frpc.toml。"
                fi
                systemctl restart frpc 2>/dev/null || systemctl start frpc 2>/dev/null || true
                echo "回退后已重启 frpc；请执行 systemctl status frpc 确认。"
            else
                echo "非 root 或无 systemd，无法自动回退；请手动从 frpc.bak.deploy / .backup_* 恢复。" >&2
            fi
        fi
    fi
fi

# ── 7. 完成 ─────────────────────────────────────────
FINAL_VERSION=$("$FRPC_BIN" --version 2>&1 || echo "unknown")
echo ""
echo "========================================="
echo "  frpc 部署完成"
echo "  版本: $FINAL_VERSION"
echo "  路径: $FRPC_BIN"
echo "  配置: $CONFIG_FILE"
echo "========================================="
