#!/bin/bash
# -*- coding: utf-8 -*-
# MySQL 安装问题修复脚本
# 用于修复 Ubuntu 24.04 上 MySQL 安装失败的问题

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}MySQL 安装问题修复脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}错误: 请使用 sudo 运行此脚本${NC}"
    exit 1
fi

echo -e "\n${YELLOW}[1/6] 停止 MySQL 服务...${NC}"
systemctl stop mysql 2>/dev/null || true
systemctl stop mysqld 2>/dev/null || true

echo -e "\n${YELLOW}[2/6] 清理 MySQL 数据目录...${NC}"
if [ -d "/var/lib/mysql" ]; then
    echo -e "${YELLOW}备份现有数据目录...${NC}"
    mv /var/lib/mysql /var/lib/mysql.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
fi

# 重新创建数据目录
mkdir -p /var/lib/mysql
chown mysql:mysql /var/lib/mysql
chmod 750 /var/lib/mysql

echo -e "\n${YELLOW}[3/6] 清理 MySQL 配置...${NC}"
rm -rf /var/lib/mysql/* 2>/dev/null || true
rm -rf /var/lib/mysql/.* 2>/dev/null || true

echo -e "\n${YELLOW}[4/6] 修复 MySQL 包配置...${NC}"
dpkg --configure -a
apt-get install -f -y

echo -e "\n${YELLOW}[5/6] 重新初始化 MySQL...${NC}"
mysqld --initialize-insecure --user=mysql --datadir=/var/lib/mysql || {
    echo -e "${RED}MySQL 初始化失败，尝试使用 --initialize${NC}"
    mysqld --initialize --user=mysql --datadir=/var/lib/mysql
}

echo -e "\n${YELLOW}[6/6] 启动 MySQL 服务...${NC}"
systemctl start mysql
systemctl enable mysql

# 等待 MySQL 启动
sleep 3

# 检查服务状态
if systemctl is-active --quiet mysql; then
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}MySQL 修复成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    # 获取临时 root 密码（如果有）
    if [ -f "/var/log/mysql/error.log" ]; then
        TEMP_PASSWORD=$(grep "temporary password" /var/log/mysql/error.log | awk '{print $NF}' | tail -1)
        if [ ! -z "$TEMP_PASSWORD" ]; then
            echo -e "\n${YELLOW}临时 root 密码: ${TEMP_PASSWORD}${NC}"
            echo -e "${YELLOW}请使用以下命令修改密码:${NC}"
            echo -e "${GREEN}sudo mysql -u root -p${NC}"
            echo -e "${GREEN}ALTER USER 'root'@'localhost' IDENTIFIED BY 'your-new-password';${NC}"
        else
            echo -e "\n${YELLOW}MySQL 已使用无密码模式初始化${NC}"
            echo -e "${YELLOW}请使用以下命令设置 root 密码:${NC}"
            echo -e "${GREEN}sudo mysql -u root${NC}"
            echo -e "${GREEN}ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'your-password';${NC}"
        fi
    fi
    
    echo -e "\n${YELLOW}测试 MySQL 连接:${NC}"
    echo -e "${GREEN}sudo systemctl status mysql${NC}"
    echo -e "${GREEN}mysql -u root -p${NC}"
else
    echo -e "\n${RED}MySQL 启动失败，请查看日志:${NC}"
    echo -e "${YELLOW}sudo journalctl -xeu mysql.service${NC}"
    echo -e "${YELLOW}sudo tail -f /var/log/mysql/error.log${NC}"
    exit 1
fi

