# 部署配置文件说明

本目录包含 Ubuntu 24.04 部署所需的所有配置文件。

## 文件结构

```
deploy/
├── systemd/
│   └── bandix-monitor.service    # systemd 服务配置文件
├── nginx/
│   └── bandix-monitor.conf      # Nginx 反向代理配置
├── gunicorn_config.py           # Gunicorn 配置文件
└── README.md                    # 本文件
```

## 使用方法

### 1. systemd 服务配置

将 `systemd/bandix-monitor.service` 复制到 `/etc/systemd/system/` 并替换变量：

```bash
sudo cp deploy/systemd/bandix-monitor.service /etc/systemd/system/bandix-monitor.service
sudo sed -i "s|{{APP_DIR}}|/opt/bandix-monitor|g" /etc/systemd/system/bandix-monitor.service
sudo sed -i "s|{{APP_USER}}|bandix|g" /etc/systemd/system/bandix-monitor.service
sudo systemctl daemon-reload
sudo systemctl enable bandix-monitor
sudo systemctl start bandix-monitor
```

### 2. Nginx 配置

将 `nginx/bandix-monitor.conf` 复制到 Nginx 配置目录并替换变量：

```bash
sudo cp deploy/nginx/bandix-monitor.conf /etc/nginx/sites-available/bandix-monitor
sudo sed -i "s|{{APP_DIR}}|/opt/bandix-monitor|g" /etc/nginx/sites-available/bandix-monitor
sudo ln -s /etc/nginx/sites-available/bandix-monitor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Gunicorn 配置

如果使用自定义 Gunicorn 配置文件，可以在 systemd 服务文件中指定：

```ini
ExecStart={{APP_DIR}}/venv/bin/gunicorn \
    --config {{APP_DIR}}/deploy/gunicorn_config.py \
    app.bandix_api:app
```

## 配置说明

### systemd 服务配置

- **User/Group**: 运行服务的用户和组
- **WorkingDirectory**: 应用工作目录
- **ExecStart**: Gunicorn 启动命令
- **Restart**: 自动重启策略
- **资源限制**: 文件描述符和进程数限制

### Nginx 配置

- **proxy_pass**: 反向代理到 Gunicorn
- **静态文件**: 直接提供静态文件服务
- **SSL/TLS**: HTTPS 配置（需要 SSL 证书）

### Gunicorn 配置

- **workers**: 工作进程数（CPU 核心数 × 2 + 1）
- **worker_class**: 工作进程类型
- **timeout**: 请求超时时间
- **日志**: 访问日志和错误日志配置

## 自定义配置

根据服务器配置调整以下参数：

1. **工作进程数**: 在 `gunicorn_config.py` 中修改 `workers`
2. **监听地址**: 修改 `bind` 参数
3. **超时时间**: 根据应用响应时间调整 `timeout`
4. **资源限制**: 在 systemd 服务文件中调整 `LimitNOFILE` 和 `LimitNPROC`

## 故障排查

### 服务无法启动

1. 检查 systemd 日志：
   ```bash
   sudo journalctl -u bandix-monitor -n 50
   ```

2. 检查配置文件语法：
   ```bash
   sudo systemd-analyze verify /etc/systemd/system/bandix-monitor.service
   ```

### Nginx 502 错误

1. 检查 Gunicorn 是否运行：
   ```bash
   sudo systemctl status bandix-monitor
   ```

2. 检查端口监听：
   ```bash
   sudo netstat -tlnp | grep 5000
   ```

3. 查看 Nginx 错误日志：
   ```bash
   sudo tail -f /var/log/nginx/bandix-monitor_error.log
   ```

## 安全建议

1. **使用非 root 用户运行**: 确保 systemd 服务使用专用用户
2. **启用 HTTPS**: 配置 SSL 证书
3. **防火墙**: 只开放必要端口
4. **资源限制**: 设置适当的系统资源限制
5. **日志轮转**: 配置日志轮转避免磁盘满

