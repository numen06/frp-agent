#!/bin/bash
# frp-agent: 在目标机读取本地 frpc 配置并 POST 导入（由服务端注入 SCAN_PATH / API_* / JSON 构造片段）
set -e

SCAN_PATH=@@SCAN_PATH@@
API_URL=@@API_URL@@
API_KEY=@@API_KEY@@
GROUP_LABEL=@@GROUP_LABEL@@

CONFIG_CONTENT=""
FIRST=true
append_block() {
  local data="$1"
  [ -z "$data" ] && return 0
  if $FIRST; then FIRST=false; else CONFIG_CONTENT="$CONFIG_CONTENT"$'\n'; fi
  CONFIG_CONTENT="$CONFIG_CONTENT$data"
}

# 1) 指定路径：文件则只读该文件；目录则只合并该目录内 *.ini / *.toml（有则用，不再扫 cwd）
# 2) 仅当指定目录下没有任何 .ini/.toml 时，才退回到当前目录扫描
SCAN_FROM_CWD=false
if [ -f "$SCAN_PATH" ]; then
  echo "[*] Reading file: $SCAN_PATH"
  append_block "$(cat "$SCAN_PATH")"
elif [ -d "$SCAN_PATH" ]; then
  CONFIG_FILES=$(find "$SCAN_PATH" -maxdepth 1 -type f \( -name "*.ini" -o -name "*.toml" \) 2>/dev/null | sort)
  for f in $CONFIG_FILES; do
    if [ -s "$f" ]; then
      echo "[*] Scanning (SCAN_PATH): $f"
      append_block "$(cat "$f")"
    fi
  done
  if [ -z "$CONFIG_CONTENT" ]; then
    SCAN_FROM_CWD=true
    echo "[*] No .ini/.toml under $SCAN_PATH, scanning current directory..."
  fi
else
  echo "[!] Not found: $SCAN_PATH"
  exit 1
fi

if [ "$SCAN_FROM_CWD" = true ]; then
  CWD_FILES=$(find . -maxdepth 1 -type f \( -name "*.ini" -o -name "*.toml" \) 2>/dev/null | sort)
  for f in $CWD_FILES; do
    if [ -s "$f" ]; then
      echo "[*] Scanning (cwd): $(pwd)/$f"
      append_block "$(cat "$f")"
    fi
  done
fi

if [ -z "$CONFIG_CONTENT" ]; then
  echo "[!] Empty config: no .ini/.toml under $SCAN_PATH nor in current directory"
  exit 1
fi

BODY=$(printf '%s' "$CONFIG_CONTENT" | python3 -c "@@PY_FOR_BASH@@")
echo "[*] Uploading to group $GROUP_LABEL ..."
RESULT=$(curl -s -S -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d "$BODY")
echo "$RESULT"
echo "[+] Done."
