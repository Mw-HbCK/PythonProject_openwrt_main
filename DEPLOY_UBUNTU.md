# Ubuntu 24.04 部署指南

本文档提供在 Ubuntu 24.04 上部署 Bandix Monitor 系统的完整指南。

## 📋 目录

- [系统要求](#系统要求)
- [快速部署（自动化脚本）](#快速部署自动化脚本)
- [手动部署](#手动部署)
- [配置说明](#配置说明)
- [服务管理](#服务管理)
- [故障排查](#故障排查)

## 系统要求

### 硬件要求

- **CPU**: 2 核或以上
- **内存**: 2GB 或以上（推荐 4GB）
- **磁盘**: 10GB 或以上可用空间
- **网络**: 能够访问 OpenWrt 设备

### 软件要求

- **操作系统**: Ubuntu 24.04 LTS
- **Python**: 3.10 或更高版本（Ubuntu 24.04 默认包含 Python 3.12）
- **MySQL**: 8.0 或更高版本（可选，也可使用 SQLite）
- **Nginx**: 1.18 或更高版本（用于反向代理）

## 快速部署（自动化脚本）

### 方法一：使用部署脚本（推荐）

```bash
# 1. 下载或克隆项目到服务器
cd /opt
sudo git clone <your-repo-url> bandix-monitor
# 或者上传项目文件到 /opt/bandix-monitor

# 2. 运行部署脚本
cd /opt/bandix-monitor
sudo chmod +x deploy.sh
sudo ./deploy.sh
```

部署脚本会自动完成：
- 安装系统依赖
- 创建 Python 虚拟环境
- 安装 Python 依赖包
- 配置 systemd 服务
- 配置 Nginx 反向代理
- 设置防火墙规则

### 方法二：使用 Ansible（适用于多服务器部署）

```bash
ansible-playbook -i inventory deploy.yml
```

## 手动部署

### 步骤 1: 更新系统

```bash
sudo apt update
sudo apt upgrade -y
```

### 步骤 2: 安装系统依赖

```bash
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    nginx \
    mysql-server \
    git \
    build-essential \
    libssl-dev \
    libffi-dev
```

### 步骤 3: 安装 MySQL（可选）

如果使用 MySQL 数据库：

```bash
# 安装 MySQL
sudo apt install -y mysql-server

# 配置 MySQL
sudo mysql_secure_installation

# 创建数据库和用户
sudo mysql -u root -p <<EOF
CREATE DATABASE bandix_monitor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE traffic_databas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'hanbo'@'localhost' IDENTIFIED BY '@HanBo123';
GRANT ALL PRIVILEGES ON bandix_monitor.* TO 'hanbo'@'localhost';
GRANT ALL PRIVILEGES ON traffic_databas.* TO 'hanbo'@'localhost';
FLUSH PRIVILEGES;
EOF
```

### 步骤 4: 创建应用用户

```bash
# 创建专用用户（可选，但推荐）
sudo useradd -m -s /bin/bash bandix
sudo mkdir -p /opt/bandix-monitor
sudo chown bandix:bandix /opt/bandix-monitor
```

### 步骤 5: 部署应用代码

```bash
# 切换到应用目录
cd /opt/bandix-monitor

# 如果使用 Git
sudo -u bandix git clone <your-repo-url> .

# 或者上传项目文件到此目录
```

### 步骤 6: 创建 Python 虚拟环境

```bash
cd /opt/bandix-monitor
sudo -u bandix python3 -m venv venv
sudo -u bandix ./venv/bin/pip install --upgrade pip
sudo -u bandix ./venv/bin/pip install -r requirements.txt
```

### 步骤 7: 安装 Gunicorn

```bash
sudo -u bandix ./venv/bin/pip install gunicorn
```

### 步骤 8: 配置应用

编辑配置文件：

```bash
sudo -u bandix nano /opt/bandix-monitor/app/config/bandix_config.ini
```

确保配置正确：
- OpenWrt 设备连接信息
- 数据库连接信息
- API 配置
- 备份和报表配置

### 步骤 9: 创建必要的目录

```bash
sudo -u bandix mkdir -p /opt/bandix-monitor/{logs,backups,reports,instance}
sudo -u bandix chmod 755 /opt/bandix-monitor/{logs,backups,reports,instance}
```

### 步骤 10: 配置 systemd 服务

创建服务文件：

```bash
sudo nano /etc/systemd/system/bandix-monitor.service
```

内容参考 `deploy/systemd/bandix-monitor.service` 文件。

然后启用并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable bandix-monitor
sudo systemctl start bandix-monitor
sudo systemctl status bandix-monitor
```

### 步骤 11: 配置 Nginx

创建 Nginx 配置：

```bash
sudo nano /etc/nginx/sites-available/bandix-monitor
```

内容参考 `deploy/nginx/bandix-monitor.conf` 文件。

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/bandix-monitor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 步骤 12: 配置防火墙

```bash
# 允许 HTTP 和 HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 如果直接访问应用（不通过 Nginx）
sudo ufw allow 5000/tcp

# 启用防火墙
sudo ufw enable
```

### 步骤 13: 初始化数据库

数据库会在首次运行时自动创建。如果需要手动初始化：

```bash
cd /opt/bandix-monitor
sudo -u bandix ./venv/bin/python3 -c "
from app.bandix_api import app
from app.models.user_models import db, User
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', role='admin', is_active=True)
        admin.set_password('your-strong-password')
        db.session.add(admin)
        db.session.commit()
        print('管理员账户创建成功')
"
```

## 配置说明

### 环境变量

可以在 systemd 服务文件中设置环境变量，或创建 `.env` 文件：

```bash
# /opt/bandix-monitor/.env
API_HOST=127.0.0.1
API_PORT=5000
DEBUG=false
BANDIX_CONFIG=/opt/bandix-monitor/app/config/bandix_config.ini
```

### 生产环境优化

1. **禁用调试模式**：确保 `debug = false` 在配置文件中
2. **使用强密码**：修改默认 API Key 和数据库密码
3. **启用 HTTPS**：配置 SSL 证书（使用 Let's Encrypt）
4. **日志轮转**：配置 logrotate
5. **定期备份**：确保备份功能已启用

### SSL/TLS 配置（使用 Let's Encrypt）

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期测试
sudo certbot renew --dry-run
```

## 服务管理

### 查看服务状态

```bash
sudo systemctl status bandix-monitor
```

### 启动/停止/重启服务

```bash
sudo systemctl start bandix-monitor
sudo systemctl stop bandix-monitor
sudo systemctl restart bandix-monitor
```

### 查看日志

```bash
# systemd 日志
sudo journalctl -u bandix-monitor -f

# 应用日志
tail -f /opt/bandix-monitor/logs/app.log
tail -f /opt/bandix-monitor/logs/app_error.log
```

### 重新加载配置

```bash
# 重启服务以应用配置更改
sudo systemctl restart bandix-monitor

# 如果只修改了 Nginx 配置
sudo nginx -t && sudo systemctl reload nginx
```

## 故障排查

### 服务无法启动

1. 检查服务状态：
   ```bash
   sudo systemctl status bandix-monitor
   ```

2. 查看详细日志：
   ```bash
   sudo journalctl -u bandix-monitor -n 100 --no-pager
   ```

3. 检查配置文件：
   ```bash
   sudo -u bandix /opt/bandix-monitor/venv/bin/python3 -c "from app.services.config_manager import load_config_file; load_config_file()"
   ```

### 数据库连接失败

1. 检查 MySQL 服务：
   ```bash
   sudo systemctl status mysql
   ```

2. 测试数据库连接：
   ```bash
   mysql -u hanbo -p -h localhost bandix_monitor
   ```

3. 检查配置文件中的数据库连接信息

### Nginx 502 错误

1. 检查 Gunicorn 是否运行：
   ```bash
   sudo systemctl status bandix-monitor
   ```

2. 检查端口是否监听：
   ```bash
   sudo netstat -tlnp | grep 5000
   ```

3. 查看 Nginx 错误日志：
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

### 性能优化

1. **调整 Gunicorn 工作进程数**：
   编辑 `/etc/systemd/system/bandix-monitor.service`，修改 `-w` 参数：
   ```bash
   ExecStart=/opt/bandix-monitor/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 ...
   ```
   工作进程数 = (CPU 核心数 × 2) + 1

2. **启用 Nginx 缓存**：
   在 Nginx 配置中添加缓存设置

3. **数据库优化**：
   - 定期清理旧数据
   - 优化数据库索引
   - 使用数据库连接池

### 备份和恢复

1. **手动备份**：
   ```bash
   sudo -u bandix /opt/bandix-monitor/venv/bin/python3 -c "
   from app.services.backup_service import create_backup
   create_backup()
   "
   ```

2. **恢复备份**：
   通过 Web 界面或 API 恢复备份文件

## 安全建议

1. **防火墙配置**：只开放必要的端口
2. **定期更新**：保持系统和依赖包更新
3. **监控日志**：定期检查错误日志
4. **备份策略**：定期备份数据库和配置文件
5. **访问控制**：使用强密码，限制管理员访问

## 更新应用

```bash
# 1. 停止服务
sudo systemctl stop bandix-monitor

# 2. 备份当前版本
sudo cp -r /opt/bandix-monitor /opt/bandix-monitor.backup

# 3. 更新代码（如果使用 Git）
cd /opt/bandix-monitor
sudo -u bandix git pull

# 4. 更新依赖
sudo -u bandix ./venv/bin/pip install -r requirements.txt --upgrade

# 5. 重启服务
sudo systemctl start bandix-monitor
sudo systemctl status bandix-monitor
```

## 卸载

```bash
# 1. 停止并禁用服务
sudo systemctl stop bandix-monitor
sudo systemctl disable bandix-monitor

# 2. 删除服务文件
sudo rm /etc/systemd/system/bandix-monitor.service
sudo systemctl daemon-reload

# 3. 删除 Nginx 配置
sudo rm /etc/nginx/sites-enabled/bandix-monitor
sudo rm /etc/nginx/sites-available/bandix-monitor
sudo systemctl reload nginx

# 4. 删除应用目录（可选）
sudo rm -rf /opt/bandix-monitor
```

## 支持

如有问题，请查看：
- 应用日志：`/opt/bandix-monitor/logs/`
- systemd 日志：`sudo journalctl -u bandix-monitor`
- Nginx 日志：`/var/log/nginx/`

---

**注意**：生产环境部署前，请务必修改所有默认密码和密钥！

