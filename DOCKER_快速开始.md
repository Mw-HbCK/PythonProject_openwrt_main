# Docker 快速开始指南

## 🚀 一键启动（最简单）

```bash
# 1. 确保已安装 Docker 和 Docker Compose
docker --version
docker-compose --version

# 2. 运行快速启动脚本
chmod +x 快速启动Docker.sh
./快速启动Docker.sh
```

## 📋 手动启动步骤

### 1. 创建环境变量文件

```bash
cp .env.example .env
nano .env
```

### 2. 编辑配置文件（可选）

```bash
nano app/config/bandix_config.ini
```

**重要配置：**
```ini
[database]
mysql_host = mysql  # 使用 Docker Compose 中的服务名
mysql_port = 3306
mysql_user = hanbo
mysql_password = @HanBo123
mysql_database = bandix_monitor
mysql_traffic_database = traffic_databas
```

### 3. 启动服务

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看状态
docker-compose ps
```

### 4. 访问应用

- **Web 界面**: http://localhost:5000
- **Nginx 代理**: http://localhost
- **API 文档**: http://localhost:5000/api/docs

## ✅ 验证部署

```bash
# 检查容器状态
docker-compose ps

# 检查健康状态
curl http://localhost:5000/health

# 查看日志
docker-compose logs -f bandix-monitor
```

## 🔧 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose stop

# 停止并删除容器
docker-compose down

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart bandix-monitor

# 进入容器
docker-compose exec bandix-monitor bash

# 重新构建
docker-compose build --no-cache
```

## 🐛 常见问题

### 端口被占用

```bash
# 检查端口
sudo netstat -tlnp | grep 5000

# 修改 docker-compose.yml 中的端口
# ports:
#   - "5001:5000"  # 改为其他端口
```

### MySQL 连接失败

```bash
# 检查 MySQL 容器
docker-compose logs mysql

# 测试连接
docker-compose exec mysql mysql -u hanbo -p@HanBo123 bandix_monitor
```

### 数据持久化

所有数据存储在 `./data` 目录：
- `data/instance/` - 数据库
- `data/logs/` - 日志
- `data/backups/` - 备份
- `data/reports/` - 报表

## 📚 详细文档

更多信息请参考 `DOCKER_部署指南.md`

---

**提示**：首次启动后，访问 http://localhost:5000 注册管理员账户。

