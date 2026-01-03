# MySQL 安装问题修复指南

## 🔍 问题描述

在 Ubuntu 24.04 上安装 MySQL 时遇到以下错误：
- `Specified filename /var/lib/mysql/ibdata1 does not exist`
- `Failed to start mysqld daemon`
- MySQL 服务无法启动

## 🚀 快速修复（推荐）

### 方法一：使用修复脚本

```bash
# 下载或创建修复脚本
chmod +x fix_mysql_install.sh
sudo ./fix_mysql_install.sh
```

### 方法二：手动修复

#### 步骤 1: 停止 MySQL 服务

```bash
sudo systemctl stop mysql
sudo systemctl stop mysqld
```

#### 步骤 2: 清理并重新创建数据目录

```bash
# 备份现有数据（如果有重要数据）
sudo mv /var/lib/mysql /var/lib/mysql.backup.$(date +%Y%m%d_%H%M%S)

# 重新创建数据目录
sudo mkdir -p /var/lib/mysql
sudo chown mysql:mysql /var/lib/mysql
sudo chmod 750 /var/lib/mysql
```

#### 步骤 3: 修复包配置

```bash
sudo dpkg --configure -a
sudo apt-get install -f -y
```

#### 步骤 4: 重新初始化 MySQL

```bash
# 方法 A: 无密码初始化（推荐用于开发环境）
sudo mysqld --initialize-insecure --user=mysql --datadir=/var/lib/mysql

# 方法 B: 生成随机密码初始化（生产环境）
sudo mysqld --initialize --user=mysql --datadir=/var/lib/mysql
```

如果使用方法 B，临时密码会在 `/var/log/mysql/error.log` 中：

```bash
sudo grep "temporary password" /var/log/mysql/error.log
```

#### 步骤 5: 启动 MySQL

```bash
sudo systemctl start mysql
sudo systemctl enable mysql
sudo systemctl status mysql
```

#### 步骤 6: 设置 root 密码

```bash
# 如果使用 --initialize-insecure
sudo mysql -u root

# 在 MySQL 中执行
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'your-strong-password';
FLUSH PRIVILEGES;
EXIT;
```

```bash
# 如果使用 --initialize（有临时密码）
sudo mysql -u root -p
# 输入临时密码，然后执行：
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'your-strong-password';
FLUSH PRIVILEGES;
EXIT;
```

## 🔄 完全重新安装（如果上述方法无效）

### 步骤 1: 完全卸载 MySQL

```bash
# 停止服务
sudo systemctl stop mysql
sudo systemctl stop mysqld

# 卸载 MySQL
sudo apt-get remove --purge mysql-server mysql-client mysql-common mysql-server-core-* mysql-client-core-*
sudo apt-get autoremove -y
sudo apt-get autoclean

# 删除数据目录
sudo rm -rf /var/lib/mysql
sudo rm -rf /var/log/mysql
sudo rm -rf /etc/mysql
```

### 步骤 2: 清理残留配置

```bash
sudo dpkg --configure -a
sudo apt-get install -f -y
```

### 步骤 3: 重新安装 MySQL

```bash
sudo apt update
sudo apt install -y mysql-server
```

### 步骤 4: 配置 MySQL

```bash
# 运行安全配置脚本
sudo mysql_secure_installation
```

## 🛠️ 创建数据库和用户（用于 Bandix Monitor）

修复 MySQL 后，创建项目所需的数据库：

```bash
sudo mysql -u root -p
```

在 MySQL 中执行：

```sql
-- 创建数据库
CREATE DATABASE IF NOT EXISTS bandix_monitor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS traffic_databas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户（如果不存在）
CREATE USER IF NOT EXISTS 'hanbo'@'localhost' IDENTIFIED BY 'your-strong-password';

-- 授予权限
GRANT ALL PRIVILEGES ON bandix_monitor.* TO 'hanbo'@'localhost';
GRANT ALL PRIVILEGES ON traffic_databas.* TO 'hanbo'@'localhost';

-- 刷新权限
FLUSH PRIVILEGES;

-- 查看用户
SELECT User, Host FROM mysql.user;

-- 退出
EXIT;
```

## ✅ 验证安装

```bash
# 检查服务状态
sudo systemctl status mysql

# 测试连接
mysql -u root -p

# 测试用户连接
mysql -u hanbo -p -h localhost bandix_monitor
```

## 🐛 常见问题

### 问题 1: 权限错误

```bash
# 修复数据目录权限
sudo chown -R mysql:mysql /var/lib/mysql
sudo chmod -R 750 /var/lib/mysql
```

### 问题 2: 端口被占用

```bash
# 检查端口
sudo netstat -tlnp | grep 3306

# 如果被占用，停止占用端口的服务或修改 MySQL 端口
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf
# 修改 port = 3306 为其他端口
```

### 问题 3: 无法连接到 MySQL

```bash
# 检查 MySQL 是否运行
sudo systemctl status mysql

# 查看错误日志
sudo tail -f /var/log/mysql/error.log

# 检查配置文件
sudo mysql --help | grep "Default options"
```

### 问题 4: 忘记 root 密码

```bash
# 停止 MySQL
sudo systemctl stop mysql

# 以安全模式启动
sudo mysqld_safe --skip-grant-tables &

# 连接 MySQL
mysql -u root

# 重置密码
USE mysql;
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'new-password';
FLUSH PRIVILEGES;
EXIT;

# 重启 MySQL
sudo systemctl restart mysql
```

## 📝 配置优化（可选）

编辑 MySQL 配置文件：

```bash
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf
```

推荐配置：

```ini
[mysqld]
# 字符集
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

# 连接数
max_connections = 200

# 缓冲区
innodb_buffer_pool_size = 1G

# 日志
slow_query_log = 1
long_query_time = 2
```

重启 MySQL：

```bash
sudo systemctl restart mysql
```

## 🔒 安全建议

1. **使用强密码**：至少 16 位，包含大小写字母、数字、特殊字符
2. **限制远程访问**：生产环境建议只允许本地连接
3. **定期备份**：配置自动备份
4. **更新系统**：保持 MySQL 和系统更新

## 📚 相关命令

```bash
# 服务管理
sudo systemctl start mysql
sudo systemctl stop mysql
sudo systemctl restart mysql
sudo systemctl status mysql

# 查看日志
sudo tail -f /var/log/mysql/error.log
sudo journalctl -u mysql -f

# 连接 MySQL
mysql -u root -p
mysql -u hanbo -p -h localhost bandix_monitor

# 导出数据库
mysqldump -u root -p bandix_monitor > backup.sql

# 导入数据库
mysql -u root -p bandix_monitor < backup.sql
```

---

**提示**：修复完成后，继续部署 Bandix Monitor 项目。

