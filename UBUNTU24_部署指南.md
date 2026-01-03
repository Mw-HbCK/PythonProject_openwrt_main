# Ubuntu 24.04 部署指南 - 快速开始

## 📋 前置检查

在开始之前，请确认已安装：
- ✅ Python 3.10+ (Ubuntu 24.04 默认包含 Python 3.12)
- ✅ pip 和 venv
- ✅ 其他必要工具

检查命令：
```bash
python3 --version
pip3 --version
```

## 🚀 方法一：源码部署（推荐用于开发/测试）

### 步骤 1: 准备环境

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装系统依赖
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

### 步骤 2: 创建应用用户

```bash
# 创建专用用户
sudo useradd -m -s /bin/bash bandix

# 创建应用目录
sudo mkdir -p /opt/bandix-monitor
sudo chown bandix:bandix /opt/bandix-monitor
```

### 步骤 3: 部署项目代码

```bash
# 方式 A: 如果使用 Git
cd /opt
sudo -u bandix git clone <your-repo-url> bandix-monitor

# 方式 B: 如果上传文件
# 将项目文件上传到 /opt/bandix-monitor
sudo chown -R bandix:bandix /opt/bandix-monitor
```

### 步骤 4: 安装 Python 依赖

```bash
cd /opt/bandix-monitor

# 创建虚拟环境
sudo -u bandix python3 -m venv venv

# 激活虚拟环境并安装依赖
sudo -u bandix ./venv/bin/pip install --upgrade pip
sudo -u bandix ./venv/bin/pip install -r requirements.txt
sudo -u bandix ./venv/bin/pip install gunicorn
```

### 步骤 5: 配置应用

```bash
# 编辑配置文件
sudo -u bandix nano /opt/bandix-monitor/app/config/bandix_config.ini
```

**重要配置项：**
```ini
[bandix]
url = http://10.0.0.1/ubus
username = root
password = your-password

[api]
host = 0.0.0.0
port = 5000
debug = false
auth_enabled = true
api_key = your-strong-api-key

[database]
mysql_host = localhost
mysql_port = 3306
mysql_user = hanbo
mysql_password = your-strong-password
mysql_database = bandix_monitor
mysql_traffic_database = traffic_databas
```

### 步骤 6: 创建必要目录

```bash
sudo -u bandix mkdir -p /opt/bandix-monitor/{logs,backups,reports,instance}
```

### 步骤 7: 配置 systemd 服务

```bash
# 创建服务文件
sudo nano /etc/systemd/system/bandix-monitor.service
```

**服务文件内容：**
```ini
[Unit]
Description=Bandix Monitor Service
After=network.target mysql.service

[Service]
Type=notify
User=bandix
Group=bandix
WorkingDirectory=/opt/bandix-monitor
Environment="PATH=/opt/bandix-monitor/venv/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="FLASK_ENV=production"
ExecStart=/opt/bandix-monitor/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:5000 \
    --timeout 120 \
    --access-logfile /opt/bandix-monitor/logs/gunicorn_access.log \
    --error-logfile /opt/bandix-monitor/logs/gunicorn_error.log \
    --log-level info \
    --preload \
    app.bandix_api:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 步骤 8: 启动服务

```bash
# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable bandix-monitor
sudo systemctl start bandix-monitor

# 检查状态
sudo systemctl status bandix-monitor
```

### 步骤 9: 配置 Nginx（可选但推荐）

```bash
# 创建 Nginx 配置
sudo nano /etc/nginx/sites-available/bandix-monitor
```

**Nginx 配置：**
```nginx
server {
    listen 80;
    server_name _;

    client_max_body_size 100M;

    access_log /var/log/nginx/bandix-monitor_access.log;
    error_log /var/log/nginx/bandix-monitor_error.log;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/bandix-monitor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 步骤 10: 配置防火墙

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 🎯 方法二：二进制部署（推荐用于生产环境）

如果您已经编译好了二进制文件：

### 步骤 1: 上传部署包

```bash
# 将编译好的部署包上传到服务器
scp build/dist/bandix-monitor-*.tar.gz user@server:/tmp/
```

### 步骤 2: 解压并部署

```bash
# SSH 登录服务器
ssh user@server

# 解压部署包
cd /opt
sudo tar -xzf /tmp/bandix-monitor-*.tar.gz
sudo mv bandix-monitor-* bandix-monitor
```

### 步骤 3: 安装系统依赖

```bash
sudo apt update
sudo apt install -y libssl3 libffi8 libsqlite3-0
```

### 步骤 4: 配置和启动

```bash
cd /opt/bandix-monitor

# 编辑配置
nano app/config/bandix_config.ini

# 设置权限
sudo chmod +x bandix-monitor start.sh
sudo useradd -m -s /bin/bash bandix
sudo chown -R bandix:bandix /opt/bandix-monitor

# 创建目录
sudo -u bandix mkdir -p logs backups reports instance

# 启动服务（使用 systemd 或直接运行）
sudo cp bandix-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bandix-monitor
sudo systemctl start bandix-monitor
```

## ✅ 验证部署

```bash
# 检查服务状态
sudo systemctl status bandix-monitor

# 查看日志
sudo journalctl -u bandix-monitor -f
tail -f /opt/bandix-monitor/logs/app.log

# 测试 API
curl http://localhost:5000/health
curl http://localhost:5000/api/docs

# 如果配置了 Nginx
curl http://localhost/
```

## 🔧 常用命令

```bash
# 服务管理
sudo systemctl start bandix-monitor
sudo systemctl stop bandix-monitor
sudo systemctl restart bandix-monitor
sudo systemctl status bandix-monitor

# 查看日志
sudo journalctl -u bandix-monitor -n 100 -f
tail -f /opt/bandix-monitor/logs/app.log
tail -f /opt/bandix-monitor/logs/app_error.log

# 重新加载配置
sudo systemctl restart bandix-monitor
sudo systemctl reload nginx
```

## 🐛 故障排查

### 服务无法启动

```bash
# 查看详细错误
sudo journalctl -u bandix-monitor -n 100 --no-pager

# 检查配置文件
sudo -u bandix /opt/bandix-monitor/venv/bin/python3 -c \
    "from app.services.config_manager import load_config_file; load_config_file()"
```

### 端口被占用

```bash
# 检查端口
sudo netstat -tlnp | grep 5000

# 修改配置文件中的端口
nano /opt/bandix-monitor/app/config/bandix_config.ini
```

### 数据库连接失败

```bash
# 检查 MySQL 服务
sudo systemctl status mysql

# 测试连接
mysql -u hanbo -p -h localhost bandix_monitor

# 创建数据库（如果需要）
sudo mysql -u root -p <<EOF
CREATE DATABASE IF NOT EXISTS bandix_monitor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS traffic_databas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'hanbo'@'localhost' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON bandix_monitor.* TO 'hanbo'@'localhost';
GRANT ALL PRIVILEGES ON traffic_databas.* TO 'hanbo'@'localhost';
FLUSH PRIVILEGES;
EOF
```

### Nginx 502 错误

```bash
# 检查 Gunicorn 是否运行
sudo systemctl status bandix-monitor

# 检查端口监听
sudo netstat -tlnp | grep 5000

# 查看 Nginx 错误日志
sudo tail -f /var/log/nginx/bandix-monitor_error.log
```

## 🔒 安全建议

1. **修改默认密码和密钥**
   ```bash
   # 修改配置文件中的密码
   nano /opt/bandix-monitor/app/config/bandix_config.ini
   ```

2. **使用强密码**
   - API Key: 至少 32 位随机字符串
   - 数据库密码: 至少 16 位，包含大小写字母、数字、特殊字符

3. **配置 SSL（推荐）**
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

4. **限制访问**
   ```bash
   # 只允许本地访问（如果使用 Nginx）
   # 在 Nginx 配置中设置
   allow 127.0.0.1;
   deny all;
   ```

## 📝 初始化数据库

数据库会在首次运行时自动创建。如果需要手动初始化：

```bash
cd /opt/bandix-monitor
sudo -u bandix ./venv/bin/python3 <<EOF
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
EOF
```

## 🎉 完成！

部署完成后，您可以：

1. 访问 Web 界面：`http://your-server-ip:5000` 或 `http://your-domain`
2. 访问 API 文档：`http://your-server-ip:5000/api/docs`
3. 注册第一个管理员账户
4. 开始使用系统

## 📚 更多帮助

- 详细部署文档：`DEPLOY_UBUNTU.md`
- 二进制部署：`二进制部署说明.md`
- 快速开始：`QUICK_START_UBUNTU.md`

---

**提示**：如果遇到问题，请查看日志文件或运行故障排查命令。

