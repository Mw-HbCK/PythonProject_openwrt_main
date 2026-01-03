# 使用 Python 3.12 官方镜像作为基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libssl-dev \
    libffi-dev \
    libmariadb-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements 文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install gunicorn

# 复制项目文件
COPY . .

# 复制并设置入口脚本权限
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# 创建必要的目录
RUN mkdir -p /app/logs /app/backups /app/reports /app/instance && \
    chmod -R 755 /app/logs /app/backups /app/reports /app/instance

# 创建非 root 用户
RUN useradd -m -u 1000 bandix && \
    chown -R bandix:bandix /app

# 切换到非 root 用户
USER bandix

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health', timeout=5)" || exit 1

# 使用入口脚本启动
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# 启动命令（使用 Gunicorn）
CMD ["gunicorn", \
     "--workers", "4", \
     "--bind", "0.0.0.0:5000", \
     "--timeout", "120", \
     "--access-logfile", "/app/logs/gunicorn_access.log", \
     "--error-logfile", "/app/logs/gunicorn_error.log", \
     "--log-level", "info", \
     "--preload", \
     "app.bandix_api:app"]

