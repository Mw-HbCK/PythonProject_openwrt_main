#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志工具模块
提供便捷的日志记录函数和上下文管理器
"""
import logging
import functools
from typing import Optional, Callable, Any
from contextlib import contextmanager

# 添加项目根目录到路径
import os
import sys
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.services.logger_service import get_logger_service


def get_logger(name: str, category: str = 'business') -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称（通常是模块名）
        category: 日志分类 (access, error, business)
        
    Returns:
        logging.Logger: 日志记录器
    """
    service = get_logger_service()
    logger = service.get_logger(name, category)
    
    # 创建一个包装器，在记录日志时自动添加分类信息
    class CategoryLogger:
        def __init__(self, logger, category):
            self._logger = logger
            self._category = category
        
        def _add_category(self, kwargs):
            if 'extra' not in kwargs:
                kwargs['extra'] = {}
            kwargs['extra']['category'] = self._category
        
        def debug(self, msg, *args, **kwargs):
            self._add_category(kwargs)
            return self._logger.debug(msg, *args, **kwargs)
        
        def info(self, msg, *args, **kwargs):
            self._add_category(kwargs)
            return self._logger.info(msg, *args, **kwargs)
        
        def warning(self, msg, *args, **kwargs):
            self._add_category(kwargs)
            return self._logger.warning(msg, *args, **kwargs)
        
        def error(self, msg, *args, **kwargs):
            self._add_category(kwargs)
            return self._logger.error(msg, *args, **kwargs)
        
        def critical(self, msg, *args, **kwargs):
            self._add_category(kwargs)
            return self._logger.critical(msg, *args, **kwargs)
        
        def exception(self, msg, *args, exc_info=True, **kwargs):
            self._add_category(kwargs)
            return self._logger.exception(msg, *args, exc_info=exc_info, **kwargs)
        
        def __getattr__(self, name):
            return getattr(self._logger, name)
    
    return CategoryLogger(logger, category)


@contextmanager
def log_request(request_info: dict):
    """
    日志上下文管理器，用于记录请求信息
    
    Args:
        request_info: 请求信息字典，包含 path, method, status_code 等
        
    Example:
        with log_request({'path': '/api/monitor', 'method': 'GET', 'status_code': 200}):
            # 处理请求
            pass
    """
    logger = get_logger('request', category='access')
    try:
        logger.info(f"请求: {request_info.get('method')} {request_info.get('path')}", 
                   extra={'extra_data': request_info})
        yield
        logger.info(f"响应: {request_info.get('method')} {request_info.get('path')} - {request_info.get('status_code')}", 
                   extra={'extra_data': request_info})
    except Exception as e:
        logger.error(f"请求错误: {request_info.get('method')} {request_info.get('path')} - {str(e)}", 
                    extra={'extra_data': request_info}, exc_info=True)
        raise


def log_function_call(func: Optional[Callable] = None, category: str = 'business'):
    """
    装饰器：自动记录函数调用
    
    Args:
        func: 被装饰的函数
        category: 日志分类
        
    Example:
        @log_function_call(category='business')
        def my_function():
            pass
    """
    def decorator(f):
        logger = get_logger(f.__module__, category)
        
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            logger.debug(f"调用函数: {f.__name__}", extra={'extra_data': {'args': str(args), 'kwargs': str(kwargs)}})
            try:
                result = f(*args, **kwargs)
                logger.debug(f"函数返回: {f.__name__}")
                return result
            except Exception as e:
                logger.error(f"函数错误: {f.__name__} - {str(e)}", exc_info=True)
                raise
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)

