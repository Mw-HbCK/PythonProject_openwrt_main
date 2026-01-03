# Docker 部署指南

本文档说明如何使用 Docker 部署 Bandix Monitor 系统。

## 📋 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 2GB 可用内存
- 至少 10GB 可用磁盘空间

## 🚀 快速开始

### 方法一：使用 Docker Compose（推荐）

#### 1. 克隆或下载项目

```bash
git clone <your-repo-url> bandix-monitor
cd bandix-monitor
```

#### 2. 配置环境变量

创建 `.env` 文件：

```bash
cp .env.example .env
nano .env
```

**`.env` 文件内容：**
```env
# MySQL 配置
MYSQL_ROOT_PASSWORD=your-strong-root-password
MYSQL_PASSWORD=@HanBo123

# 应用配置
SECRET_KEY=your-very-strong-secret-key-here

# 管理员账户（首次启动时创建）
ADMIN_PASSWORD=admin123456
INIT_DB=true
```

#### 3. 编辑配置文件（可选）

如果需要自定义配置，编辑 `app/config/bandix_config.ini`：

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

[database]
mysql_host = mysql
mysql_port = 3306
mysql_user = hanbo
mysql_password = @HanBo123
mysql_database = bandix_monitor
mysql_traffic_database = traffic_databas
```

#### 4. 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看服务状态
docker-compose ps
```

#### 5. 访问应用

- Web 界面: http://localhost:5000
- Nginx 代理: http://localhost
- API 文档: http://localhost:5000/api/docs

### 方法二：仅使用 Docker（不使用 Compose）

#### 1. 构建镜像

```bash
docker build -t bandix-monitor:latest .
```

#### 2. 运行容器

```bash
# 创建数据目录
mkdir -p ./data/{instance,logs,backups,reports}

# 运行容器
docker run -d \
  --name bandix-monitor \
  -p 5000:5000 \
  -v $(pwd)/app/config/bandix_config.ini:/app/app/config/bandix_config.ini:ro \
  -v $(pwd)/data/instance:/app/instance \
  -v $(pwd)/data/logs:/app/logs \
  -v $(pwd)/data/backups:/app/backups \
  -v $(pwd)/data/reports:/app/reports \
  -e FLASK_ENV=production \
  -e SECRET_KEY=your-secret-key \
  --restart unless-stopped \
  bandix-monitor:latest
```

## 📁 目录结构

```
bandix-monitor/
├── Dockerfile                 # Docker 镜像构建文件
├── docker-compose.yml         # Docker Compose 配置
├── docker-entrypoint.sh       # 容器启动脚本
├── .dockerignore             # Docker 忽略文件
├── .env                       # 环境变量配置（需创建）
├── docker/
│   ├── mysql/
│   │   └── init.sql          # MySQL 初始化脚本
│   └── nginx/
│       ├── nginx.conf        # Nginx 主配置
│       └── conf.d/
│           └── bandix-monitor.conf  # Nginx 站点配置
└── data/                     # 数据目录（自动创建）
    ├── instance/            # 数据库文件
    ├── logs/                # 日志文件
    ├── backups/             # 备份文件
    └── reports/             # 报表文件
```

## ⚙️ 配置说明

### 环境变量

在 `.env` 文件或 `docker-compose.yml` 中设置：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MYSQL_ROOT_PASSWORD` | MySQL root 密码 | `root123456` |
| `MYSQL_PASSWORD` | MySQL 用户密码 | `@HanBo123` |
| `SECRET_KEY` | Flask 密钥 | `change-this-secret-key` |
| `ADMIN_PASSWORD` | 管理员初始密码 | `admin123456` |
| `INIT_DB` | 是否初始化数据库 | `true` |

### 端口映射

- `5000:5000` - 应用服务端口
- `3306:3306` - MySQL 端口（可选，如果使用外部 MySQL）
- `80:80` - Nginx HTTP 端口
- `443:443` - Nginx HTTPS 端口（需要配置 SSL）

### 数据持久化

所有数据存储在 `./data` 目录下：
- `data/instance/` - 数据库文件
- `data/logs/` - 日志文件
- `data/backups/` - 备份文件
- `data/reports/` - 报表文件

## 🔧 常用命令

### Docker Compose 命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose stop

# 停止并删除容器
docker-compose down

# 查看日志
docker-compose logs -f bandix-monitor
docker-compose logs -f mysql

# 重启服务
docker-compose restart bandix-monitor

# 查看服务状态
docker-compose ps

# 进入容器
docker-compose exec bandix-monitor bash

# 重新构建镜像
docker-compose build --no-cache

# 更新并重启
docker-compose pull
docker-compose up -d
```

### Docker 命令

```bash
# 查看容器
docker ps

# 查看日志
docker logs -f bandix-monitor

# 进入容器
docker exec -it bandix-monitor bash

# 停止容器
docker stop bandix-monitor

# 删除容器
docker rm bandix-monitor

# 查看镜像
docker images

# 删除镜像
docker rmi bandix-monitor:latest
```

## 🔍 验证部署

```bash
# 检查容器状态
docker-compose ps

# 检查健康状态
docker-compose exec bandix-monitor python -c "import requests; print(requests.get('http://localhost:5000/health').json())"

# 测试 API
curl http://localhost:5000/health
curl http://localhost:5000/api/docs
```

## 🐛 故障排查

### 容器无法启动

```bash
# 查看详细日志
docker-compose logs bandix-monitor

# 检查配置
docker-compose config

# 进入容器调试
docker-compose exec bandix-monitor bash
```

### MySQL 连接失败

```bash
# 检查 MySQL 容器
docker-compose logs mysql

# 测试 MySQL 连接
docker-compose exec mysql mysql -u hanbo -p@HanBo123 bandix_monitor

# 检查网络
docker network ls
docker network inspect bandix-monitor_bandix-network
```

### 端口冲突

```bash
# 检查端口占用
sudo netstat -tlnp | grep 5000
sudo netstat -tlnp | grep 3306

# 修改 docker-compose.yml 中的端口映射
# ports:
#   - "5001:5000"  # 改为其他端口
```

### 数据丢失

数据存储在 `./data` 目录，确保：
1. 目录权限正确
2. 使用卷挂载（不要使用匿名卷）
3. 定期备份 `./data` 目录

## 🔒 安全建议

1. **修改默认密码**
   - 修改 `.env` 文件中的密码
   - 修改配置文件中的 API Key

2. **使用外部 MySQL**（生产环境推荐）
   ```yaml
   # 在 docker-compose.yml 中删除 mysql 服务
   # 修改环境变量指向外部 MySQL
   environment:
     - MYSQL_HOST=your-mysql-host
     - MYSQL_PORT=3306
   ```

3. **配置 SSL/TLS**
   - 使用 Let's Encrypt
   - 配置 Nginx SSL

4. **限制访问**
   - 使用防火墙
   - 配置 Nginx 访问控制

## 📊 性能优化

1. **调整工作进程数**
   编辑 `Dockerfile` 中的 `--workers` 参数

2. **资源限制**
   在 `docker-compose.yml` 中添加：
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 2G
   ```

3. **数据库优化**
   - 使用外部 MySQL
   - 配置连接池
   - 优化查询

## 🔄 更新应用

```bash
# 停止服务
docker-compose down

# 备份数据
cp -r ./data ./data.backup

# 拉取最新代码
git pull

# 重新构建镜像
docker-compose build --no-cache

# 启动服务
docker-compose up -d
```

## 📦 备份和恢复

### 备份

```bash
# 备份数据目录
tar -czf bandix-monitor-backup-$(date +%Y%m%d).tar.gz ./data

# 备份 MySQL（如果使用容器内 MySQL）
docker-compose exec mysql mysqldump -u root -p bandix_monitor > backup.sql
```

### 恢复

```bash
# 恢复数据目录
tar -xzf bandix-monitor-backup-YYYYMMDD.tar.gz

# 恢复 MySQL
docker-compose exec -T mysql mysql -u root -p bandix_monitor < backup.sql
```

## 🎯 生产环境部署

### 1. 使用外部 MySQL

修改 `docker-compose.yml`，删除 `mysql` 服务，修改环境变量指向外部数据库。

### 2. 配置域名和 SSL

```bash
# 安装 certbot
docker run -it --rm \
  -v certbot-certs:/etc/letsencrypt \
  certbot/certbot certonly --standalone -d your-domain.com
```

### 3. 使用 Docker Swarm 或 Kubernetes

参考相应的编排文档。

## 📚 相关文档

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [项目 README](README.md)

---

**提示**：首次部署后，请访问 http://localhost:5000 注册管理员账户。

