# Ubuntu 24.04 快速部署指南

## 🚀 一键部署（推荐）

```bash
# 1. 上传项目到服务器
scp -r . user@your-server:/opt/bandix-monitor

# 2. SSH 登录服务器
ssh user@your-server

# 3. 运行部署脚本
cd /opt/bandix-monitor
sudo chmod +x deploy.sh
sudo ./deploy.sh
```

## 📝 手动部署步骤

### 1. 安装依赖

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx mysql-server git
```

### 2. 创建用户和目录

```bash
sudo useradd -m -s /bin/bash bandix
sudo mkdir -p /opt/bandix-monitor
sudo chown bandix:bandix /opt/bandix-monitor
```

### 3. 部署代码

```bash
# 上传项目文件到 /opt/bandix-monitor
cd /opt/bandix-monitor
sudo -u bandix python3 -m venv venv
sudo -u bandix ./venv/bin/pip install -r requirements.txt
sudo -u bandix ./venv/bin/pip install gunicorn
```

### 4. 配置应用

```bash
# 编辑配置文件
sudo -u bandix nano /opt/bandix-monitor/app/config/bandix_config.ini

# 创建必要目录
sudo -u bandix mkdir -p /opt/bandix-monitor/{logs,backups,reports,instance}
```

### 5. 配置 systemd

```bash
# 复制服务文件
sudo cp deploy/systemd/bandix-monitor.service /etc/systemd/system/
sudo sed -i "s|{{APP_DIR}}|/opt/bandix-monitor|g" /etc/systemd/system/bandix-monitor.service
sudo sed -i "s|{{APP_USER}}|bandix|g" /etc/systemd/system/bandix-monitor.service

# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable bandix-monitor
sudo systemctl start bandix-monitor
```

### 6. 配置 Nginx

```bash
# 复制 Nginx 配置
sudo cp deploy/nginx/bandix-monitor.conf /etc/nginx/sites-available/bandix-monitor
sudo sed -i "s|{{APP_DIR}}|/opt/bandix-monitor|g" /etc/nginx/sites-available/bandix-monitor

# 启用站点
sudo ln -s /etc/nginx/sites-available/bandix-monitor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. 配置防火墙

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## ✅ 验证部署

```bash
# 检查服务状态
sudo systemctl status bandix-monitor

# 检查端口
sudo netstat -tlnp | grep 5000

# 访问应用
curl http://localhost:5000/health
```

## 🔧 常用命令

```bash
# 启动/停止/重启服务
sudo systemctl start bandix-monitor
sudo systemctl stop bandix-monitor
sudo systemctl restart bandix-monitor

# 查看日志
sudo journalctl -u bandix-monitor -f
tail -f /opt/bandix-monitor/logs/app.log

# 重新加载配置
sudo systemctl restart bandix-monitor
sudo systemctl reload nginx
```

## 📚 详细文档

更多详细信息请参考 [DEPLOY_UBUNTU.md](DEPLOY_UBUNTU.md)

