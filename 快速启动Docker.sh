#!/bin/bash
# Docker 快速启动脚本

echo "=========================================="
echo "Bandix Monitor Docker 快速启动"
echo "=========================================="

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: 未安装 Docker，请先安装 Docker"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "错误: 未安装 Docker Compose，请先安装 Docker Compose"
    exit 1
fi

# 创建 .env 文件（如果不存在）
if [ ! -f .env ]; then
    echo "创建 .env 文件..."
    cat > .env <<EOF
# MySQL 配置
MYSQL_ROOT_PASSWORD=root123456
MYSQL_PASSWORD=@HanBo123

# 应用配置
SECRET_KEY=$(openssl rand -hex 32)
ADMIN_PASSWORD=admin123456
INIT_DB=true
EOF
    echo ".env 文件已创建，请根据需要修改"
fi

# 创建数据目录
mkdir -p data/{instance,logs,backups,reports}

# 启动服务
echo "启动 Docker 服务..."
if command -v docker-compose &> /dev/null; then
    docker-compose up -d
else
    docker compose up -d
fi

# 等待服务启动
echo "等待服务启动..."
sleep 5

# 显示服务状态
echo ""
echo "=========================================="
echo "服务状态:"
echo "=========================================="
if command -v docker-compose &> /dev/null; then
    docker-compose ps
else
    docker compose ps
fi

echo ""
echo "=========================================="
echo "访问地址:"
echo "=========================================="
echo "  - Web 界面: http://localhost:5000"
echo "  - Nginx 代理: http://localhost"
echo "  - API 文档: http://localhost:5000/api/docs"
echo ""
echo "查看日志: docker-compose logs -f"
echo "停止服务: docker-compose down"
echo ""

