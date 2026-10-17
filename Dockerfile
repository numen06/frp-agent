# 多阶段构建：前端 + 后端

# ============ 阶段 1: 构建前端 ============
# 使用阿里云 Node.js 镜像加速下载
FROM alibaba-cloud-linux-3-registry.cn-hangzhou.cr.aliyuncs.com/alinux3/node:20.16 AS frontend-builder

# 切换到 root 用户以创建目录
USER root

# 创建所需目录并设置权限
RUN mkdir -p /app/frontend /app/dist && \
    chown -R node:node /app/frontend /app/dist

# 设置工作目录
WORKDIR /app/frontend

# 切换到 node 用户
USER node

# 设置 Node.js 环境变量（构建时需要 devDependencies，所以不设置 NODE_ENV=production）
ENV NODE_OPTIONS="--max-old-space-size=4096"

# 仅复制依赖文件以利用缓存
COPY --chown=node:node frontend/package*.json ./

# 安装依赖（包括 devDependencies，因为 vite 在 devDependencies 中）
RUN npm config set registry https://registry.npmmirror.com && \
    npm install --legacy-peer-deps && \
    npm cache clean --force

# 复制剩余前端代码并构建
COPY --chown=node:node frontend/ ./

# 构建生产版本（输出到 /app/dist）
RUN npm run build


# FreeRDP terminates mstsc sessions and maps platform accounts to stored credentials.
FROM debian:trixie-slim AS rdp-builder
ARG FREERDP_VERSION=3.15.0+dfsg-2.1+deb13u3
RUN apt-get update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
    gcc libc6-dev pkg-config freerdp3-dev=${FREERDP_VERSION} libwinpr3-dev=${FREERDP_VERSION} libcurl4-openssl-dev libjson-c-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY gateway/rdp/proxy-frpagent.c ./
RUN gcc -shared -fPIC -O2 -Wall -Wextra -Wno-unused-parameter -Wno-deprecated-declarations -Werror \
    -o /src/proxy-frpagent-plugin.so proxy-frpagent.c \
    $(pkg-config --cflags --libs freerdp-server-proxy3 freerdp3 winpr3 libcurl json-c openssl)

# Keep proxy runtime and module ABI on the same Debian release.
FROM python:3.11-slim-trixie
ARG FREERDP_VERSION=3.15.0+dfsg-2.1+deb13u3
RUN apt-get update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
    freerdp3-proxy=${FREERDP_VERSION} libcurl4t64 libjson-c5 ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

# 维护者信息
LABEL maintainer="frp-agent"
LABEL version="1.2.0"
LABEL description="FRP Agent Management Platform"

# 设置工作目录
WORKDIR /app

# 设置时区
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

# 复制依赖文件
COPY backend/requirements.txt .
# 安装 Python 依赖
# 可选：为 pip 配置阿里云镜像源以加速下载
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip install --no-cache-dir -r requirements.txt

# 从第一阶段复制构建好的前端文件（vite.config.js 中 outDir 设置为 '../dist'）
COPY --from=frontend-builder /app/dist ./dist
# 复制后端代码
COPY backend/ ./backend/
COPY --from=rdp-builder /src/proxy-frpagent-plugin.so /usr/lib/x86_64-linux-gnu/freerdp3/proxy/proxy-frpagent-plugin.so

# 创建数据目录和日志目录
RUN mkdir -p /app/data /app/logs

# 暴露端口
EXPOSE 8000 2222 23750 13389

# 应用环境变量
ENV APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    SSH_GATEWAY_ENABLED=true \
    SSH_GATEWAY_HOST=0.0.0.0 \
    SSH_GATEWAY_PORT=2222 \
    DOCKER_GATEWAY_ENABLED=true \
    DOCKER_GATEWAY_HOST=0.0.0.0 \
    DOCKER_GATEWAY_PORT=23750 \
    DOCKER_GATEWAY_TLS_COMMON_NAME=localhost \
    APP_DEBUG=false \
    AUTH_USERNAME=admin \
    AUTH_PASSWORD=admin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 启动命令
# 启动后端服务（后端会服务前端构建文件）
# 端口可通过环境变量 APP_PORT 设置
CMD ["python", "backend/app.py"]

