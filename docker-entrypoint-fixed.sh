#!/bin/bash
# Docker 容器启动入口脚本（修复权限问题版本）

set -e

echo "=========================================="
echo "Bandix Monitor 容器启动中..."
echo "=========================================="

# 创建必要的目录（如果不存在）
# 注意：目录权限已在 Dockerfile 中设置，这里只需要确保目录存在
mkdir -p /app/logs /app/backups /app/reports /app/instance 2>/dev/null || true

# 等待 MySQL 就绪（如果使用 MySQL）
if [ -n "$MYSQL_HOST" ] && [ "$MYSQL_HOST" != "localhost" ] && [ "$MYSQL_HOST" != "127.0.0.1" ]; then
    echo "等待 MySQL 数据库就绪..."
    until python -c "import pymysql; pymysql.connect(host='$MYSQL_HOST', port=${MYSQL_PORT:-3306}, user='${MYSQL_USER:-root}', password='${MYSQL_PASSWORD}')" 2>/dev/null; do
        echo "MySQL 未就绪，等待 2 秒..."
        sleep 2
    done
    echo "MySQL 已就绪！"
fi

# 初始化数据库（如果需要）
if [ "$INIT_DB" = "true" ]; then
    echo "初始化数据库..."
    python -c "
from app.bandix_api import app
from app.models.user_models import db, User
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', role='admin', is_active=True)
        admin.set_password('${ADMIN_PASSWORD:-admin123456}')
        db.session.add(admin)
        db.session.commit()
        print('管理员账户创建成功: admin / ${ADMIN_PASSWORD:-admin123456}')
    else:
        print('管理员账户已存在')
" 2>/dev/null || echo "数据库初始化跳过（可能已存在）"
fi

echo "=========================================="
echo "启动应用服务..."
echo "=========================================="

# 执行传入的命令（通常是 gunicorn）
exec "$@"

