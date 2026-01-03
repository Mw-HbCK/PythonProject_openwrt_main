#!/bin/bash
# -*- coding: utf-8 -*-
# Ubuntu 24.04 一键部署脚本
# 自动完成所有部署步骤

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置变量
APP_NAME="bandix-monitor"
APP_USER="bandix"
APP_DIR="/opt/${APP_NAME}"
SERVICE_NAME="${APP_NAME}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Bandix Monitor Ubuntu 24.04 一键部署${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}错误: 请使用 sudo 运行此脚本${NC}"
    exit 1
fi

# 步骤 1: 更新系统
echo -e "\n${YELLOW}[1/12] 更新系统包...${NC}"
apt update
apt upgrade -y

# 步骤 2: 安装系统依赖
echo -e "\n${YELLOW}[2/12] 安装系统依赖...${NC}"
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
echo -e "\n${YELLOW}[3/12] 创建应用用户...${NC}"
if ! id "$APP_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$APP_USER"
    echo -e "${GREEN}用户 $APP_USER 创建成功${NC}"
else
    echo -e "${YELLOW}用户 $APP_USER 已存在${NC}"
fi

# 步骤 4: 创建应用目录
echo -e "\n${YELLOW}[4/12] 创建应用目录...${NC}"
mkdir -p "$APP_DIR"
chown "$APP_USER:$APP_USER" "$APP_DIR"

# 步骤 5: 检查项目文件
echo -e "\n${YELLOW}[5/12] 检查项目文件...${NC}"
if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}检测到项目文件，复制到应用目录...${NC}"
    cp -r . "$APP_DIR/" 2>/dev/null || {
        echo -e "${YELLOW}部分文件复制失败，请手动检查${NC}"
    }
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
else
    echo -e "${RED}错误: 未找到 requirements.txt，请确保在项目根目录运行此脚本${NC}"
    exit 1
fi

# 步骤 6: 创建 Python 虚拟环境
echo -e "\n${YELLOW}[6/12] 创建 Python 虚拟环境...${NC}"
cd "$APP_DIR"
sudo -u "$APP_USER" python3 -m venv venv
sudo -u "$APP_USER" ./venv/bin/pip install --upgrade pip setuptools wheel

# 步骤 7: 安装 Python 依赖
echo -e "\n${YELLOW}[7/12] 安装 Python 依赖...${NC}"
sudo -u "$APP_USER" ./venv/bin/pip install -r requirements.txt
sudo -u "$APP_USER" ./venv/bin/pip install gunicorn

# 步骤 8: 创建必要的目录
echo -e "\n${YELLOW}[8/12] 创建必要的目录...${NC}"
sudo -u "$APP_USER" mkdir -p "$APP_DIR"/{logs,backups,reports,instance}
sudo -u "$APP_USER" chmod 755 "$APP_DIR"/{logs,backups,reports,instance}

# 步骤 9: 配置 systemd 服务
echo -e "\n${YELLOW}[9/12] 配置 systemd 服务...${NC}"
if [ -f "deploy/systemd/bandix-monitor.service" ]; then
    cp deploy/systemd/bandix-monitor.service /etc/systemd/system/${SERVICE_NAME}.service
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
Environment="FLASK_ENV=production"
ExecStart=$APP_DIR/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:5000 \
    --timeout 120 \
    --access-logfile $APP_DIR/logs/gunicorn_access.log \
    --error-logfile $APP_DIR/logs/gunicorn_error.log \
    --log-level info \
    --preload \
    app.bandix_api:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
fi

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"

# 步骤 10: 配置 Nginx
echo -e "\n${YELLOW}[10/12] 配置 Nginx...${NC}"
if [ -f "deploy/nginx/bandix-monitor.conf" ]; then
    cp deploy/nginx/bandix-monitor.conf /etc/nginx/sites-available/${SERVICE_NAME}
    sed -i "s|{{APP_DIR}}|$APP_DIR|g" /etc/nginx/sites-available/${SERVICE_NAME}
else
    cat > /etc/nginx/sites-available/${SERVICE_NAME} <<EOF
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
}
EOF
fi

if [ ! -L /etc/nginx/sites-enabled/${SERVICE_NAME} ]; then
    ln -s /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/
fi

nginx -t
systemctl reload nginx

# 步骤 11: 配置防火墙
echo -e "\n${YELLOW}[11/12] 配置防火墙...${NC}"
if command -v ufw &> /dev/null; then
    ufw allow 80/tcp
    ufw allow 443/tcp
    echo -e "${GREEN}防火墙规则已添加${NC}"
else
    echo -e "${YELLOW}未安装 ufw，跳过防火墙配置${NC}"
fi

# 步骤 12: 提示配置
echo -e "\n${YELLOW}[12/12] 配置检查...${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "\n${YELLOW}重要：请完成以下配置${NC}"
echo -e "1. 编辑配置文件:"
echo -e "   ${BLUE}sudo nano ${APP_DIR}/app/config/bandix_config.ini${NC}"
echo -e ""
echo -e "2. 配置 MySQL 数据库（如果使用）:"
echo -e "   ${BLUE}sudo mysql_secure_installation${NC}"
echo -e "   ${BLUE}sudo mysql -u root -p${NC}"
echo -e ""
echo -e "3. 启动服务:"
echo -e "   ${BLUE}sudo systemctl start ${SERVICE_NAME}${NC}"
echo -e ""
echo -e "4. 检查服务状态:"
echo -e "   ${BLUE}sudo systemctl status ${SERVICE_NAME}${NC}"
echo -e ""
echo -e "5. 查看日志:"
echo -e "   ${BLUE}sudo journalctl -u ${SERVICE_NAME} -f${NC}"
echo -e ""

echo -e "${YELLOW}访问地址：${NC}"
echo -e "  - 直接访问: ${BLUE}http://$(hostname -I | awk '{print $1}'):5000${NC}"
echo -e "  - Nginx 代理: ${BLUE}http://$(hostname -I | awk '{print $1}')${NC}"
echo -e "  - API 文档: ${BLUE}http://$(hostname -I | awk '{print $1}'):5000/api/docs${NC}"
echo -e ""

echo -e "${RED}安全提示：${NC}"
echo -e "  - 请修改配置文件中的默认密码和 API Key"
echo -e "  - 建议配置 SSL 证书（使用 Let's Encrypt）"
echo -e "  - 确保防火墙规则正确配置"
echo -e ""

