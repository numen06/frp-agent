#!/usr/bin/env bash
set -euo pipefail
umask 077

install_dir=${FRP_AGENT_DIR:-"$HOME/frp-agent"}
image=${FRP_AGENT_IMAGE:-registry.cn-shanghai.aliyuncs.com/numen/frp-agent:latest}
container=frp-agent

docker info >/dev/null
if docker container inspect "$container" >/dev/null 2>&1; then
  printf '容器 %s 已存在。升级请先备份数据，再按 README 的升级步骤操作。\n' "$container" >&2
  exit 1
fi

mkdir -p "$install_dir/data"
install_dir=$(cd -- "$install_dir" && pwd -P)
env_file="$install_dir/.env"
initial_password=
if [[ ! -e "$env_file" && ! -L "$env_file" ]]; then
  if [[ -e "$install_dir/data/frp_agent.db" ]]; then
    printf '发现已有数据库。请先恢复 %s，以保留原加密密钥。\n' "$env_file" >&2
    exit 1
  fi
  initial_password=$(od -v -An -N16 -tx1 /dev/urandom | tr -d '[:space:]')
  credential_secret=$(od -v -An -N32 -tx1 /dev/urandom | tr -d '[:space:]')
  (set -C; printf 'AUTH_PASSWORD=%s\nSSH_CREDENTIAL_SECRET=%s\n' \
    "$initial_password" "$credential_secret" > "$env_file")
fi
if ! grep -q '^AUTH_PASSWORD=.' "$env_file" || ! grep -q '^SSH_CREDENTIAL_SECRET=.' "$env_file"; then
  printf '请在 %s 中设置 AUTH_PASSWORD 和 SSH_CREDENTIAL_SECRET，再运行安装。已有部署请保留原加密密钥。\n' "$env_file" >&2
  exit 1
fi

docker pull --platform linux/amd64 "$image"
docker run -d --platform linux/amd64 --name "$container" --restart unless-stopped \
  --env-file "$env_file" \
  --mount "type=bind,source=$install_dir/data,target=/app/data" \
  -p 8000:8000 -p 2222:2222 -p 23750:23750 -p 13389:13389 \
  -p 7000:7000 -p 6000-6099:6000-6099/tcp -p 6000-6099:6000-6099/udp \
  "$image" >/dev/null

for ((attempt=0; attempt<30; attempt++)); do
  if curl --noproxy '*' -fsS --max-time 1 http://127.0.0.1:8000/api/public/version >/dev/null 2>&1; then
    printf 'FRP-AGENT 已启动。访问 http://服务器IP:8000（本机可用 http://localhost:8000）。\n'
    printf '默认用户名：admin；配置文件：%s\n' "$env_file"
    if [[ -n "$initial_password" ]]; then
      printf '初始密码：%s\n' "$initial_password"
    fi
    exit 0
  fi
  sleep 1
done

printf '容器已创建，但 Web 服务尚未就绪。请运行 docker logs %s 查看启动日志。\n' "$container" >&2
exit 1
