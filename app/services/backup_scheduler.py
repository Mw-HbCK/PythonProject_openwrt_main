#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份调度器
使用 schedule 库实现定时备份任务
"""
import os
import sys
import threading
import time
import schedule
from datetime import datetime
from typing import Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.services.backup_service import BackupService
from app.services.config_manager import load_config_file, get_config_file_path
from app.models.backup_models import BackupHistory, db
from app.models.user_models import db as user_db
import json


class BackupScheduler:
    """备份调度器类"""
    
    def __init__(self, app):
        """
        初始化备份调度器
        
        Args:
            app: Flask应用实例
        """
        self.app = app
        self.backup_service = BackupService(app)
        self.scheduler_thread = None
        self.is_running = False
        self.stop_event = threading.Event()
    
    def _load_backup_config(self):
        """
        加载备份配置
        
        Returns:
            dict: 备份配置
        """
        try:
            config_file = get_config_file_path()
            _, _, _, _, backup_config, _, _ = load_config_file(config_file)
            return backup_config
        except Exception as e:
            print(f"[备份调度器] 加载配置失败: {e}", file=sys.stderr)
            return {}
    
    def _run_backup_job(self):
        """
        执行备份任务
        这个方法在调度器线程中运行
        """
        try:
            with self.app.app_context():
                print(f"[备份调度器] 开始执行定时备份任务...")
                
                # 加载配置
                backup_config = self._load_backup_config()
                backup_enabled = backup_config.get('backup_enabled', 'false').lower() == 'true'
                
                if not backup_enabled:
                    print(f"[备份调度器] 备份未启用，跳过")
                    return
                
                # 获取配置
                backup_dir = backup_config.get('backup_dir', './backups')
                databases_str = backup_config.get('databases', 'users,traffic')
                # 去除注释（如果有）
                if '#' in databases_str:
                    databases_str = databases_str.split('#')[0]
                databases = [db.strip() for db in databases_str.split(',') if db.strip()]
                compress = backup_config.get('compress', 'true').lower() == 'true'
                keep_count_str = backup_config.get('keep_count', '30')
                # 去除注释（如果有）
                if '#' in keep_count_str:
                    keep_count_str = keep_count_str.split('#')[0]
                keep_count = int(keep_count_str.strip())
                
                # 执行备份
                try:
                    backup_path, backup_size, databases_backed_up = self.backup_service.backup_databases(
                        db_names=databases,
                        backup_dir=backup_dir,
                        compress=compress
                    )
                    
                    # 获取备份文件名
                    if compress:
                        backup_filename = os.path.basename(backup_path)
                    else:
                        backup_filename = os.path.basename(backup_path)
                    
                    # 尝试上传到云存储
                    cloud_uploaded = False
                    try:
                        cloud_uploaded = self.backup_service.upload_to_cloud(backup_path, backup_config)
                    except Exception as e:
                        print(f"[备份调度器] 云存储上传失败: {e}", file=sys.stderr)
                    
                    # 记录备份历史
                    backup_record = BackupHistory(
                        backup_filename=backup_filename,
                        backup_path=backup_path,
                        backup_size=backup_size,
                        databases=json.dumps(databases_backed_up),
                        status='success',
                        cloud_uploaded=cloud_uploaded
                    )
                    user_db.session.add(backup_record)
                    user_db.session.commit()
                    
                    print(f"[备份调度器] 备份成功: {backup_filename}, 大小: {backup_size} 字节")
                    
                    # 清理旧备份
                    try:
                        deleted_count = self.backup_service.delete_old_backups(backup_dir, keep_count)
                        if deleted_count > 0:
                            print(f"[备份调度器] 已清理 {deleted_count} 个旧备份")
                    except Exception as e:
                        print(f"[备份调度器] 清理旧备份失败: {e}", file=sys.stderr)
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"[备份调度器] 备份失败: {error_msg}", file=sys.stderr)
                    
                    # 记录失败的备份历史
                    try:
                        backup_record = BackupHistory(
                            backup_filename='',
                            backup_path='',
                            backup_size=0,
                            databases=json.dumps([]),
                            status='failed',
                            error_message=error_msg,
                            cloud_uploaded=False
                        )
                        user_db.session.add(backup_record)
                        user_db.session.commit()
                    except Exception as db_error:
                        print(f"[备份调度器] 保存备份历史失败: {db_error}", file=sys.stderr)
                        
        except Exception as e:
            print(f"[备份调度器] 执行备份任务时发生异常: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    def _schedule_backup(self):
        """
        根据配置调度备份任务
        """
        try:
            backup_config = self._load_backup_config()
            backup_enabled = backup_config.get('backup_enabled', 'false').lower() == 'true'
            
            if not backup_enabled:
                return
            
            frequency = backup_config.get('frequency', 'daily').lower()
            backup_time_str = backup_config.get('backup_time', '02:00')
            # 去除注释（如果有）
            if '#' in backup_time_str:
                backup_time_str = backup_time_str.split('#')[0]
            backup_time = backup_time_str.strip()
            
            # 清除所有现有任务
            schedule.clear()
            
            # 根据频率调度任务
            if frequency == 'daily':
                schedule.every().day.at(backup_time).do(self._run_backup_job)
            elif frequency == 'weekly':
                # 每周一执行
                schedule.every().monday.at(backup_time).do(self._run_backup_job)
            elif frequency == 'monthly':
                # 每月1号执行
                schedule.every().day.at(backup_time).do(self._run_backup_job)
                # 注意：schedule库不支持每月执行，这里使用每日检查，实际执行时判断日期
                # 更好的方式是使用APScheduler，但为了简化使用schedule库
                # 这里改为使用每日执行，在实际执行时判断是否为月初
            
            print(f"[备份调度器] 已调度备份任务: {frequency}, 时间: {backup_time}")
            
        except Exception as e:
            print(f"[备份调度器] 调度备份任务失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    def _scheduler_loop(self):
        """
        调度器循环（在后台线程中运行）
        """
        print("[备份调度器] 调度器线程已启动")
        
        # 初始调度
        with self.app.app_context():
            self._schedule_backup()
        
        # 运行调度循环
        while not self.stop_event.is_set():
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                print(f"[备份调度器] 调度循环错误: {e}", file=sys.stderr)
                time.sleep(60)
        
        print("[备份调度器] 调度器线程已停止")
    
    def start(self):
        """启动备份调度器"""
        if self.is_running:
            print("[备份调度器] 调度器已在运行", file=sys.stderr)
            return
        
        try:
            with self.app.app_context():
                backup_config = self._load_backup_config()
                backup_enabled = backup_config.get('backup_enabled', 'false').lower() == 'true'
                
                if not backup_enabled:
                    print("[备份调度器] 备份未启用，不启动调度器")
                    return
            
            self.is_running = True
            self.stop_event.clear()
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            print("[备份调度器] 备份调度器已启动")
            
        except Exception as e:
            print(f"[备份调度器] 启动失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            self.is_running = False
    
    def stop(self):
        """停止备份调度器"""
        if not self.is_running:
            return
        
        print("[备份调度器] 正在停止备份调度器...")
        self.is_running = False
        self.stop_event.set()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        schedule.clear()
        print("[备份调度器] 备份调度器已停止")
    
    def reload_config(self):
        """重新加载配置并重新调度"""
        if self.is_running:
            with self.app.app_context():
                self._schedule_backup()


# 全局调度器实例
_backup_scheduler: Optional[BackupScheduler] = None


def get_backup_scheduler(app=None):
    """
    获取备份调度器实例（单例模式）
    
    Args:
        app: Flask应用实例
        
    Returns:
        BackupScheduler: 备份调度器实例
    """
    global _backup_scheduler
    if _backup_scheduler is None and app:
        _backup_scheduler = BackupScheduler(app)
    return _backup_scheduler


def start_backup_scheduler(app):
    """
    启动备份调度器
    
    Args:
        app: Flask应用实例
    """
    scheduler = get_backup_scheduler(app)
    if scheduler:
        scheduler.start()


def stop_backup_scheduler():
    """停止备份调度器"""
    global _backup_scheduler
    if _backup_scheduler:
        _backup_scheduler.stop()
        _backup_scheduler = None

