# Docker 权限问题修复指南

## 🔍 问题描述

容器启动时出现权限错误：
```
chmod: changing permissions of '/app/logs': Operation not permitted
```

这是因为在非 root 用户下尝试修改目录权限导致的。

## ✅ 解决方案

### 方法一：使用修复后的文件（推荐）

已修复 `docker-entrypoint.sh` 和 `Dockerfile`，重新构建镜像：

```bash
# 停止并删除旧容器
docker-compose down

# 重新构建镜像
docker-compose build --no-cache

# 启动服务
docker-compose up -d
```

### 方法二：临时使用 root 用户（不推荐，仅用于测试）

如果急需运行，可以临时修改 Dockerfile：

```dockerfile
# 注释掉切换到非 root 用户
# USER bandix
```

然后重新构建。

### 方法三：使用卷挂载时设置权限

如果使用卷挂载，确保宿主机目录权限正确：

```bash
# 创建数据目录并设置权限
mkdir -p ./data/{instance,logs,backups,reports}
chmod -R 755 ./data

# 或者在 docker-compose.yml 中使用 user 选项
volumes:
  - ./data/logs:/app/logs:rw,uid=1000,gid=1000
```

## 🔧 修复说明

### 1. Dockerfile 修复

- 在切换到非 root 用户**之前**设置目录权限
- 确保所有文件和目录都属于 `bandix` 用户

### 2. docker-entrypoint.sh 修复

- 移除了 `chmod` 命令（权限已在构建时设置）
- 使用 `mkdir -p` 确保目录存在（不会报错）
- 添加了错误处理

## 📋 验证修复

```bash
# 重新构建并启动
docker-compose build --no-cache
docker-compose up -d

# 查看日志，应该没有权限错误
docker-compose logs bandix-monitor

# 检查容器内权限
docker-compose exec bandix-monitor ls -la /app
```

## 🐛 其他权限问题

### 问题：无法写入日志文件

```bash
# 检查卷挂载权限
docker-compose exec bandix-monitor touch /app/logs/test.log

# 如果失败，检查宿主机目录权限
ls -la ./data/logs
chmod -R 755 ./data
```

### 问题：无法创建数据库文件

```bash
# 检查 instance 目录权限
docker-compose exec bandix-monitor ls -la /app/instance

# 如果使用卷挂载，确保目录可写
chmod -R 755 ./data/instance
```

## 📝 最佳实践

1. **在 Dockerfile 中设置权限**：在切换到非 root 用户之前设置所有权限
2. **使用非 root 用户运行**：提高安全性
3. **卷挂载时注意权限**：确保宿主机目录权限正确
4. **避免在运行时修改权限**：所有权限设置应在构建时完成

## 🔄 完整重建步骤

```bash
# 1. 停止并删除所有容器和卷
docker-compose down -v

# 2. 清理旧镜像（可选）
docker rmi bandix-monitor_bandix-monitor 2>/dev/null || true

# 3. 重新构建
docker-compose build --no-cache

# 4. 启动服务
docker-compose up -d

# 5. 查看日志确认无错误
docker-compose logs -f bandix-monitor
```

---

**提示**：如果问题仍然存在，请检查 Docker 版本和系统权限设置。

