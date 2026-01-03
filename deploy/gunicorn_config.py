# -*- coding: utf-8 -*-
# Gunicorn 配置文件
# 用于生产环境部署

import multiprocessing
import os

# 服务器配置
bind = "127.0.0.1:5000"
backlog = 2048

# 工作进程配置
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5

# 性能优化
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# 日志配置
accesslog = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "gunicorn_access.log")
errorlog = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "gunicorn_error.log")
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程命名
proc_name = "bandix-monitor"

# 用户和组（在 systemd 中设置）
# user = "bandix"
# group = "bandix"

# 安全设置
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# 其他配置
daemon = False
pidfile = None
umask = 0
tmp_upload_dir = None

def when_ready(server):
    """服务器启动就绪时的回调"""
    server.log.info("Bandix Monitor 服务已启动")

def on_exit(server):
    """服务器退出时的回调"""
    server.log.info("Bandix Monitor 服务已停止")

