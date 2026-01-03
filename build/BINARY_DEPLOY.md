# 二进制文件部署指南

本文档说明如何将 Bandix Monitor 编译为二进制文件并在 Ubuntu 24.04 上部署。

## 📦 编译二进制文件

### 方法一：使用打包脚本（推荐）

```bash
# 1. 进入项目目录
cd /path/to/bandix-monitor

# 2. 运行打包脚本
chmod +x build/build_binary.sh
./build/build_binary.sh
```

打包完成后，二进制文件位于 `build/dist/bandix-monitor/` 目录。

### 方法二：手动打包

```bash
# 1. 安装依赖
pip install pyinstaller

# 2. 运行 PyInstaller
cd /path/to/bandix-monitor
pyinstaller build/pyinstaller.spec
```

## 🚀 部署二进制文件

### 步骤 1: 准备服务器

```bash
# 安装必要的系统依赖（仅运行时需要）
sudo apt update
sudo apt install -y libssl3 libffi8 libsqlite3-0
```

### 步骤 2: 上传部署包

```bash
# 将 build/dist/bandix-monitor 目录上传到服务器
scp -r build/dist/bandix-monitor user@server:/opt/bandix-monitor
```

### 步骤 3: 配置应用

```bash
# SSH 登录服务器
ssh user@server

# 进入应用目录
cd /opt/bandix-monitor

# 编辑配置文件
nano app/config/bandix_config.ini
```

### 步骤 4: 设置权限

```bash
# 创建专用用户（可选）
sudo useradd -m -s /bin/bash bandix

# 设置文件权限
sudo chown -R bandix:bandix /opt/bandix-monitor
sudo chmod +x /opt/bandix-monitor/bandix-monitor
sudo chmod +x /opt/bandix-monitor/start.sh

# 创建必要目录
sudo -u bandix mkdir -p /opt/bandix-monitor/{logs,backups,reports,instance}
```

### 步骤 5: 启动服务

#### 方式一：直接运行

```bash
cd /opt/bandix-monitor
./start.sh
```

#### 方式二：使用 systemd（推荐）

```bash
# 1. 复制服务文件
sudo cp /opt/bandix-monitor/bandix-monitor.service /etc/systemd/system/

# 2. 修改服务文件中的路径（如果需要）
sudo nano /etc/systemd/system/bandix-monitor.service

# 3. 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable bandix-monitor
sudo systemctl start bandix-monitor

# 4. 检查状态
sudo systemctl status bandix-monitor
```

## ⚙️ 配置说明

### 环境变量

可以在启动脚本或 systemd 服务文件中设置：

```bash
export FLASK_ENV=production
export SECRET_KEY=your-secret-key
export API_HOST=0.0.0.0
export API_PORT=5000
```

### 配置文件

编辑 `app/config/bandix_config.ini`：

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
api_key = your-api-key
```

## 🔍 验证部署

```bash
# 检查服务状态
sudo systemctl status bandix-monitor

# 查看日志
tail -f /opt/bandix-monitor/logs/app.log

# 测试 API
curl http://localhost:5000/health
```

## 📋 目录结构

```
/opt/bandix-monitor/
├── bandix-monitor          # 可执行文件
├── start.sh                # 启动脚本
├── bandix-monitor.service   # systemd 服务文件
├── app/
│   └── config/
│       └── bandix_config.ini
├── logs/                   # 日志目录
├── backups/                # 备份目录
├── reports/                # 报表目录
└── instance/               # 数据库目录
```

## 🛠️ 常用操作

### 启动/停止服务

```bash
# 使用 systemd
sudo systemctl start bandix-monitor
sudo systemctl stop bandix-monitor
sudo systemctl restart bandix-monitor

# 或直接运行
cd /opt/bandix-monitor
./start.sh
```

### 查看日志

```bash
# systemd 日志
sudo journalctl -u bandix-monitor -f

# 应用日志
tail -f /opt/bandix-monitor/logs/app.log
```

### 更新应用

```bash
# 1. 停止服务
sudo systemctl stop bandix-monitor

# 2. 备份当前版本
sudo cp -r /opt/bandix-monitor /opt/bandix-monitor.backup

# 3. 上传新版本
# (上传新的二进制文件)

# 4. 设置权限
sudo chmod +x /opt/bandix-monitor/bandix-monitor

# 5. 启动服务
sudo systemctl start bandix-monitor
```

## 🔒 安全建议

1. **使用非 root 用户运行**
   ```bash
   sudo useradd -m -s /bin/bash bandix
   sudo chown -R bandix:bandix /opt/bandix-monitor
   ```

2. **配置防火墙**
   ```bash
   sudo ufw allow 5000/tcp
   sudo ufw enable
   ```

3. **使用 Nginx 反向代理**
   参考 `deploy/nginx/bandix-monitor.conf`

4. **定期备份**
   确保备份功能已启用

## 🐛 故障排查

### 二进制文件无法运行

```bash
# 检查文件权限
ls -l /opt/bandix-monitor/bandix-monitor

# 检查依赖库
ldd /opt/bandix-monitor/bandix-monitor

# 检查系统库
sudo apt install -y libssl3 libffi8 libsqlite3-0
```

### 服务无法启动

```bash
# 查看详细错误
sudo journalctl -u bandix-monitor -n 100 --no-pager

# 手动运行测试
cd /opt/bandix-monitor
./bandix-monitor
```

### 配置文件找不到

确保配置文件位于 `app/config/bandix_config.ini`，或设置环境变量：

```bash
export BANDIX_CONFIG=/path/to/bandix_config.ini
```

## 📊 性能优化

1. **使用 systemd 管理服务**（推荐）
2. **配置 Nginx 反向代理**
3. **启用数据库连接池**
4. **定期清理日志和旧数据**

## 📝 注意事项

1. **二进制文件大小**：打包后的文件可能较大（100-200MB），因为包含了所有依赖
2. **系统兼容性**：二进制文件需要在相同架构的系统上运行（x86_64）
3. **配置文件**：首次运行前必须配置 `bandix_config.ini`
4. **数据库**：确保数据库服务已启动（如果使用 MySQL）

## 🔄 从源码部署迁移到二进制部署

如果之前使用源码部署，迁移到二进制部署：

```bash
# 1. 备份当前配置和数据
sudo cp -r /opt/bandix-monitor /opt/bandix-monitor.backup

# 2. 停止旧服务
sudo systemctl stop bandix-monitor

# 3. 部署二进制文件
# (上传新的二进制文件)

# 4. 复制配置文件
cp /opt/bandix-monitor.backup/app/config/bandix_config.ini \
   /opt/bandix-monitor/app/config/

# 5. 复制数据库文件（如果使用 SQLite）
cp /opt/bandix-monitor.backup/instance/* \
   /opt/bandix-monitor/instance/ 2>/dev/null || true

# 6. 启动新服务
sudo systemctl start bandix-monitor
```

---

**提示**：二进制部署适合不需要修改代码的场景，如果需要频繁更新代码，建议使用源码部署。

