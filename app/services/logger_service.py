#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志服务
提供日志初始化、管理和配置功能
"""
import os
import sys
import json
import logging
import gzip
import shutil
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
from typing import Dict, Optional, Any

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class JSONFormatter(logging.Formatter):
    """JSON格式日志格式化器"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 添加额外字段
        if hasattr(record, 'category'):
            log_data['category'] = record.category
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """文本格式日志格式化器"""
    
    def __init__(self, include_category=True):
        super().__init__()
        self.include_category = include_category
    
    def format(self, record):
        # 基础格式：时间戳 [级别] [日志器] 消息
        if self.include_category and hasattr(record, 'category'):
            format_str = '%(asctime)s [%(levelname)s] [%(category)s] [%(name)s] %(message)s'
        else:
            format_str = '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
        
        formatter = logging.Formatter(
            format_str,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        return formatter.format(record)


class LoggerService:
    """日志服务类"""
    
    def __init__(self):
        self.log_dir = None
        self.loggers = {}
        self.handlers = {}
        self.initialized = False
    
    def init_logging(self, config: Dict[str, Any]):
        """
        初始化日志系统
        
        Args:
            config: 日志配置字典
        """
        try:
            # 获取配置
            log_level = config.get('log_level', 'INFO').upper()
            log_format = config.get('log_format', 'both').lower()
            log_dir = config.get('log_dir', './logs')
            log_max_bytes = int(config.get('log_max_bytes', 10)) * 1024 * 1024  # 转换为字节
            log_backup_count = int(config.get('log_backup_count', 30))
            log_rotation = config.get('log_rotation', 'both').lower()
            log_to_console = config.get('log_to_console', 'true').lower() == 'true'
            log_to_file = config.get('log_to_file', 'true').lower() == 'true'
            log_categories = config.get('log_categories', 'all').lower()
            
            # 设置日志级别
            level = getattr(logging, log_level, logging.INFO)
            
            # 创建日志目录
            self.log_dir = os.path.abspath(log_dir)
            os.makedirs(self.log_dir, exist_ok=True)
            os.makedirs(os.path.join(self.log_dir, 'archive'), exist_ok=True)
            
            # 确定日志分类
            categories = []
            if log_categories == 'all':
                categories = ['access', 'error', 'business', 'all']
            else:
                categories = [cat.strip() for cat in log_categories.split(',')]
            
            # 创建格式化器
            json_formatter = JSONFormatter()
            text_formatter = TextFormatter(include_category=True)
            
            # 为每个分类创建日志记录器
            for category in categories:
                logger_name = f'app_{category}' if category != 'all' else 'app'
                logger = logging.getLogger(logger_name)
                logger.setLevel(level)
                logger.propagate = False  # 防止日志传播到根日志记录器
                
                # 清除现有处理器
                logger.handlers.clear()
                
                # 控制台处理器
                if log_to_console:
                    console_handler = logging.StreamHandler(sys.stdout)
                    console_handler.setLevel(level)
                    if log_format in ['json', 'both']:
                        console_handler.setFormatter(json_formatter)
                    else:
                        console_handler.setFormatter(text_formatter)
                    logger.addHandler(console_handler)
                
                # 文件处理器
                if log_to_file:
                    log_file = os.path.join(self.log_dir, f'{logger_name}.log')
                    
                    # 根据滚动策略选择处理器
                    if log_rotation == 'size':
                        file_handler = RotatingFileHandler(
                            log_file,
                            maxBytes=log_max_bytes,
                            backupCount=log_backup_count,
                            encoding='utf-8'
                        )
                    elif log_rotation == 'time':
                        file_handler = TimedRotatingFileHandler(
                            log_file,
                            when='midnight',
                            interval=1,
                            backupCount=log_backup_count,
                            encoding='utf-8'
                        )
                    else:  # both
                        # 使用TimedRotatingFileHandler，并在回调中处理大小限制
                        file_handler = TimedRotatingFileHandler(
                            log_file,
                            when='midnight',
                            interval=1,
                            backupCount=log_backup_count,
                            encoding='utf-8'
                        )
                    
                    file_handler.setLevel(level)
                    if log_format in ['json', 'both']:
                        file_handler.setFormatter(json_formatter)
                    else:
                        file_handler.setFormatter(text_formatter)
                    logger.addHandler(file_handler)
                    
                    # 注册处理器以便后续管理
                    self.handlers[logger_name] = file_handler
                
                self.loggers[logger_name] = logger
            
            # 设置根日志记录器
            root_logger = logging.getLogger()
            root_logger.setLevel(level)
            
            self.initialized = True
            
        except Exception as e:
            print(f"[日志服务] 初始化失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    def get_logger(self, name: str, category: str = 'business') -> logging.Logger:
        """
        获取日志记录器
        
        Args:
            name: 日志记录器名称
            category: 日志分类 (access, error, business)
            
        Returns:
            logging.Logger: 日志记录器
        """
        if not self.initialized:
            # 如果未初始化，返回一个基本的日志记录器
            return logging.getLogger(name)
        
        # 根据分类选择日志记录器
        if category == 'access':
            base_logger = self.loggers.get('app_access', logging.getLogger('app_access'))
        elif category == 'error':
            base_logger = self.loggers.get('app_error', logging.getLogger('app_error'))
        elif category == 'business':
            base_logger = self.loggers.get('app_business', logging.getLogger('app_business'))
        else:
            base_logger = self.loggers.get('app', logging.getLogger('app'))
        
        # 创建子日志记录器
        logger = logging.getLogger(f'{base_logger.name}.{name}')
        logger.setLevel(base_logger.level)
        
        # 如果没有处理器，继承父日志记录器的处理器
        if not logger.handlers:
            logger.handlers = base_logger.handlers[:]
        
        return logger
    
    def compress_old_logs(self):
        """
        压缩旧的日志文件
        """
        try:
            if not self.log_dir:
                return
            
            archive_dir = os.path.join(self.log_dir, 'archive')
            os.makedirs(archive_dir, exist_ok=True)
            
            # 查找所有.log文件（排除当前正在使用的）
            for filename in os.listdir(self.log_dir):
                if not filename.endswith('.log'):
                    continue
                
                filepath = os.path.join(self.log_dir, filename)
                if not os.path.isfile(filepath):
                    continue
                
                # 检查是否已经压缩
                if filename.endswith('.gz'):
                    continue
                
                # 检查文件是否正在使用（通过检查是否有对应的.lock文件或最近修改时间）
                # 这里简单判断：如果文件最近1小时内被修改，则认为正在使用
                file_mtime = os.path.getmtime(filepath)
                if (datetime.now().timestamp() - file_mtime) < 3600:
                    continue
                
                # 压缩文件
                compressed_filename = f"{filename}.gz"
                compressed_path = os.path.join(archive_dir, compressed_filename)
                
                if not os.path.exists(compressed_path):
                    with open(filepath, 'rb') as f_in:
                        with gzip.open(compressed_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # 删除原文件
                    os.remove(filepath)
                    
        except Exception as e:
            print(f"[日志服务] 压缩日志文件失败: {e}", file=sys.stderr)
    
    def get_log_files(self) -> list:
        """
        获取所有日志文件列表
        
        Returns:
            list: 日志文件信息列表
        """
        files = []
        try:
            if not self.log_dir or not os.path.exists(self.log_dir):
                return files
            
            for filename in os.listdir(self.log_dir):
                filepath = os.path.join(self.log_dir, filename)
                if os.path.isfile(filepath) and filename.endswith('.log'):
                    stat = os.stat(filepath)
                    files.append({
                        'name': filename,
                        'path': filepath,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            
            # 也包含归档目录中的文件
            archive_dir = os.path.join(self.log_dir, 'archive')
            if os.path.exists(archive_dir):
                for filename in os.listdir(archive_dir):
                    filepath = os.path.join(archive_dir, filename)
                    if os.path.isfile(filepath) and (filename.endswith('.log') or filename.endswith('.gz')):
                        stat = os.stat(filepath)
                        files.append({
                            'name': f'archive/{filename}',
                            'path': filepath,
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
            
        except Exception as e:
            print(f"[日志服务] 获取日志文件列表失败: {e}", file=sys.stderr)
        
        return files


# 全局日志服务实例
_logger_service = None


def get_logger_service() -> LoggerService:
    """获取全局日志服务实例"""
    global _logger_service
    if _logger_service is None:
        _logger_service = LoggerService()
    return _logger_service


def init_logging(config: Dict[str, Any]):
    """初始化日志系统（便捷函数）"""
    service = get_logger_service()
    service.init_logging(config)

