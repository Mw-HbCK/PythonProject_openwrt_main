#!/bin/bash
# -*- coding: utf-8 -*-
# Ubuntu 24.04 自动化部署脚本
# Bandix Monitor 部署脚本

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量
APP_NAME="bandix-monitor"
APP_USER="bandix"
APP_DIR="/opt/${APP_NAME}"
SERVICE_NAME="${APP_NAME}"
NGINX_SITE="${APP_NAME}"

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}错误: 请使用 sudo 运行此脚本${NC}"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Bandix Monitor 自动化部署脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 步骤 1: 更新系统
echo -e "\n${YELLOW}[1/10] 更新系统包...${NC}"
apt update
apt upgrade -y

# 步骤 2: 安装系统依赖
echo -e "\n${YELLOW}[2/10] 安装系统依赖...${NC}"
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    nginx \
    mysql-server \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    curl

# 步骤 3: 创建应用用户
echo -e "\n${YELLOW}[3/10] 创建应用用户...${NC}"
if ! id "$APP_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$APP_USER"
    echo -e "${GREEN}用户 $APP_USER 创建成功${NC}"
else
    echo -e "${YELLOW}用户 $APP_USER 已存在${NC}"
fi

# 步骤 4: 创建应用目录
echo -e "\n${YELLOW}[4/10] 创建应用目录...${NC}"
mkdir -p "$APP_DIR"
chown "$APP_USER:$APP_USER" "$APP_DIR"

# 如果当前目录有项目文件，复制到应用目录
if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}检测到项目文件，复制到应用目录...${NC}"
    cp -r . "$APP_DIR/"
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
else
    echo -e "${YELLOW}未检测到项目文件，请确保项目文件在 $APP_DIR 目录${NC}"
fi

# 步骤 5: 创建 Python 虚拟环境
echo -e "\n${YELLOW}[5/10] 创建 Python 虚拟环境...${NC}"
cd "$APP_DIR"
sudo -u "$APP_USER" python3 -m venv venv
sudo -u "$APP_USER" ./venv/bin/pip install --upgrade pip setuptools wheel

# 步骤 6: 安装 Python 依赖
echo -e "\n${YELLOW}[6/10] 安装 Python 依赖...${NC}"
sudo -u "$APP_USER" ./venv/bin/pip install -r requirements.txt
sudo -u "$APP_USER" ./venv/bin/pip install gunicorn

# 步骤 7: 创建必要的目录
echo -e "\n${YELLOW}[7/10] 创建必要的目录...${NC}"
sudo -u "$APP_USER" mkdir -p "$APP_DIR"/{logs,backups,reports,instance}
sudo -u "$APP_USER" chmod 755 "$APP_DIR"/{logs,backups,reports,instance}

# 步骤 8: 配置 systemd 服务
echo -e "\n${YELLOW}[8/10] 配置 systemd 服务...${NC}"
if [ -f "deploy/systemd/bandix-monitor.service" ]; then
    cp deploy/systemd/bandix-monitor.service /etc/systemd/system/${SERVICE_NAME}.service
    # 替换路径变量
    sed -i "s|{{APP_DIR}}|$APP_DIR|g" /etc/systemd/system/${SERVICE_NAME}.service
    sed -i "s|{{APP_USER}}|$APP_USER|g" /etc/systemd/system/${SERVICE_NAME}.service
else
    # 创建默认 systemd 服务文件
    cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Bandix Monitor Service
After=network.target mysql.service

[Service]
Type=notify
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=$APP_DIR/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:5000 \
    --timeout 120 \
    --access-logfile $APP_DIR/logs/gunicorn_access.log \
    --error-logfile $APP_DIR/logs/gunicorn_error.log \
    --log-level info \
    --preload \
    app.bandix_api:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
fi

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"

# 步骤 9: 配置 Nginx
echo -e "\n${YELLOW}[9/10] 配置 Nginx...${NC}"
if [ -f "deploy/nginx/bandix-monitor.conf" ]; then
    cp deploy/nginx/bandix-monitor.conf /etc/nginx/sites-available/${NGINX_SITE}
    # 替换路径变量
    sed -i "s|{{APP_DIR}}|$APP_DIR|g" /etc/nginx/sites-available/${NGINX_SITE}
else
    # 创建默认 Nginx 配置
    cat > /etc/nginx/sites-available/${NGINX_SITE} <<EOF
server {
    listen 80;
    server_name _;

    client_max_body_size 100M;

    access_log /var/log/nginx/${APP_NAME}_access.log;
    error_log /var/log/nginx/${APP_NAME}_error.log;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /static {
        alias $APP_DIR/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF
fi

# 启用站点
if [ ! -L /etc/nginx/sites-enabled/${NGINX_SITE} ]; then
    ln -s /etc/nginx/sites-available/${NGINX_SITE} /etc/nginx/sites-enabled/
fi

# 测试 Nginx 配置
nginx -t

# 步骤 10: 配置防火墙
echo -e "\n${YELLOW}[10/10] 配置防火墙...${NC}"
if command -v ufw &> /dev/null; then
    ufw allow 80/tcp
    ufw allow 443/tcp
    echo -e "${GREEN}防火墙规则已添加${NC}"
else
    echo -e "${YELLOW}未安装 ufw，跳过防火墙配置${NC}"
fi

# 完成
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\n${YELLOW}下一步操作：${NC}"
echo -e "1. 编辑配置文件: ${APP_DIR}/app/config/bandix_config.ini"
echo -e "2. 初始化数据库（如果需要）"
echo -e "3. 启动服务: sudo systemctl start ${SERVICE_NAME}"
echo -e "4. 启动 Nginx: sudo systemctl reload nginx"
echo -e "5. 查看服务状态: sudo systemctl status ${SERVICE_NAME}"
echo -e "\n${YELLOW}重要提示：${NC}"
echo -e "- 请修改配置文件中的默认密码和密钥"
echo -e "- 确保 MySQL 服务已启动（如果使用 MySQL）"
echo -e "- 检查防火墙设置"
echo -e "\n"

