#!/bin/bash
# 快速修复 MySQL 安装问题

echo "正在修复 MySQL 安装问题..."

# 停止 MySQL
sudo systemctl stop mysql 2>/dev/null || true

# 备份并清理数据目录
if [ -d "/var/lib/mysql" ]; then
    sudo mv /var/lib/mysql /var/lib/mysql.backup.$(date +%Y%m%d_%H%M%S)
fi

# 重新创建目录
sudo mkdir -p /var/lib/mysql
sudo chown mysql:mysql /var/lib/mysql
sudo chmod 750 /var/lib/mysql

# 修复包
sudo dpkg --configure -a
sudo apt-get install -f -y

# 重新初始化（无密码模式）
sudo mysqld --initialize-insecure --user=mysql --datadir=/var/lib/mysql

# 启动 MySQL
sudo systemctl start mysql
sudo systemctl enable mysql

# 等待启动
sleep 3

# 设置 root 密码
sudo mysql <<EOF
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'root123456';
FLUSH PRIVILEGES;
EOF

echo "MySQL 修复完成！"
echo "root 密码: root123456"
echo "请尽快修改密码！"

