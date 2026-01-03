-- MySQL 初始化脚本
-- 创建数据库和用户

-- 创建数据库
CREATE DATABASE IF NOT EXISTS bandix_monitor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS traffic_databas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户（如果不存在）
CREATE USER IF NOT EXISTS 'hanbo'@'%' IDENTIFIED BY '@HanBo123';

-- 授予权限
GRANT ALL PRIVILEGES ON bandix_monitor.* TO 'hanbo'@'%';
GRANT ALL PRIVILEGES ON traffic_databas.* TO 'hanbo'@'%';

-- 刷新权限
FLUSH PRIVILEGES;

