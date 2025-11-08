# 使用阿里云的 Python 3.11 轻量级镜像作为基础
FROM alibaba-cloud-linux-3-registry.cn-hangzhou.cr.aliyuncs.com/alinux3/python:3.11.1

# 设置工作目录
WORKDIR /app

# 设置时区
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

# 复制依赖文件
COPY requirements.txt .



# 维护者信息
LABEL maintainer="frp-agent"
LABEL version="1.0"
LABEL description="FRP Agent Management Platform"

# 设置工作目录
WORKDIR /app


# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
# 可选：为 pip 配置阿里云镜像源以加速下载
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/
COPY app.py ./

# 创建数据目录和日志目录
RUN mkdir -p /app/data /app/logs

# 暴露端口
EXPOSE 8000


# 应用环境变量
ENV APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    APP_DEBUG=false \
    AUTH_USERNAME=admin \
    AUTH_PASSWORD=admin123 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 启动命令
CMD ["python", "app.py"]

