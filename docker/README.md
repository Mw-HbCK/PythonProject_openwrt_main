# Docker 配置文件说明

本目录包含 Docker 部署相关的配置文件。

## 📁 文件结构

```
docker/
├── mysql/
│   └── init.sql              # MySQL 初始化脚本
└── nginx/
    ├── nginx.conf            # Nginx 主配置文件
    └── conf.d/
        └── bandix-monitor.conf  # Bandix Monitor 站点配置
```

## 🔧 配置说明

### MySQL 初始化脚本

`mysql/init.sql` 在 MySQL 容器首次启动时自动执行，用于：
- 创建数据库
- 创建用户
- 授予权限

### Nginx 配置

- `nginx.conf` - Nginx 主配置文件
- `conf.d/bandix-monitor.conf` - 应用反向代理配置

## 📝 自定义配置

### 修改 MySQL 初始化

编辑 `docker/mysql/init.sql`，添加自定义 SQL 语句。

### 修改 Nginx 配置

编辑 `docker/nginx/conf.d/bandix-monitor.conf`，可以：
- 添加 SSL 配置
- 修改代理设置
- 添加访问控制

## 🚀 使用

这些配置文件会在 `docker-compose up` 时自动加载，无需手动操作。

