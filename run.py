#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bandix Monitor API 启动脚本
"""
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app.bandix_api import app, logger, error_logger
from app.services.data_collector import start_collector
from app.services.notification_queue import start_workers, stop_workers
from app.services.backup_scheduler import start_backup_scheduler, stop_backup_scheduler
from app.services.report_scheduler import start_report_scheduler, stop_report_scheduler

if __name__ == "__main__":
    # 从环境变量获取参数，如果没有则使用默认值
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "5000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    if logger:
        logger.info(f"启动 Bandix Monitor API 服务...")
        logger.info(f"监听地址: http://{host}:{port}")
        logger.info(f"用户中心: http://{host}:{port}/")
        logger.info(f"数据查询: http://{host}:{port}/data")
    else:
        print(f"启动 Bandix Monitor API 服务...")
        print(f"监听地址: http://{host}:{port}")
        print(f"用户中心: http://{host}:{port}/")
        print(f"数据查询: http://{host}:{port}/data")
    
    # 启动数据收集服务（自动启动，使用配置的API密钥）
    log_msg = "启动数据收集服务（每1秒收集一次）..."
    if logger:
        logger.info(log_msg)
    else:
        print(log_msg)
    try:
        start_collector()
        if logger:
            logger.info("数据收集服务已启动")
        else:
            print("数据收集服务已启动")
    except Exception as e:
        if error_logger:
            error_logger.error(f"数据收集服务启动失败: {e}", exc_info=True)
        else:
            print(f"警告: 数据收集服务启动失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    # 启动通知任务队列工作线程
    log_msg = "启动通知任务队列..."
    if logger:
        logger.info(log_msg)
    else:
        print(log_msg)
    try:
        start_workers(app, num_workers=4)
        if logger:
            logger.info("通知任务队列已启动")
        else:
            print("通知任务队列已启动")
    except Exception as e:
        if error_logger:
            error_logger.error(f"通知任务队列启动失败: {e}", exc_info=True)
        else:
            print(f"警告: 通知任务队列启动失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    # 启动备份调度器
    log_msg = "启动备份调度器..."
    if logger:
        logger.info(log_msg)
    else:
        print(log_msg)
    try:
        start_backup_scheduler(app)
        if logger:
            logger.info("备份调度器已启动")
        else:
            print("备份调度器已启动")
    except Exception as e:
        if error_logger:
            error_logger.error(f"备份调度器启动失败: {e}", exc_info=True)
        else:
            print(f"警告: 备份调度器启动失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    # 启动报表调度器
    log_msg = "启动报表调度器..."
    if logger:
        logger.info(log_msg)
    else:
        print(log_msg)
    try:
        start_report_scheduler(app)
        if logger:
            logger.info("报表调度器已启动")
        else:
            print("报表调度器已启动")
    except Exception as e:
        if error_logger:
            error_logger.error(f"报表调度器启动失败: {e}", exc_info=True)
        else:
            print(f"警告: 报表调度器启动失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    try:
        app.run(host=host, port=port, debug=debug)
    finally:
        # 确保在应用关闭时停止工作线程和调度器
        stop_workers()
        stop_backup_scheduler()
        stop_report_scheduler()

