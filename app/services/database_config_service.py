#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库配置服务
提供数据库配置的读取、保存、验证功能
"""
import os
import sys
from typing import Dict, Optional, Tuple
from urllib.parse import quote_plus

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.services.config_manager import get_config_file_path, load_config_file, save_config_file


def get_database_config() -> Dict:
    """
    获取数据库配置
    
    Returns:
        dict: 数据库配置字典
    """
    config_file = get_config_file_path()
    _, _, _, _, _, _, _, database_config = load_config_file(config_file)
    return database_config or {}


def save_database_config(database_config: Dict) -> bool:
    """
    保存数据库配置
    
    Args:
        database_config: 数据库配置字典
        
    Returns:
        bool: 是否保存成功
    """
    config_file = get_config_file_path()
    try:
        save_config_file(database_config=database_config, config_file_path=config_file)
        return True
    except Exception as e:
        raise Exception(f"保存数据库配置失败: {e}")


def get_database_uri(database_config: Optional[Dict] = None) -> Tuple[str, Optional[str]]:
    """
    根据MySQL配置生成SQLAlchemy数据库URI
    
    Args:
        database_config: 数据库配置字典，如果为None则从配置文件读取
        
    Returns:
        tuple: (database_uri, bind_key)
            - database_uri: SQLAlchemy数据库URI
            - bind_key: 绑定键（None，主数据库不使用bind_key）
    """
    if database_config is None:
        database_config = get_database_config()
    
    mysql_host = database_config.get('mysql_host', 'localhost')
    mysql_port = database_config.get('mysql_port', '3306')
    mysql_user = database_config.get('mysql_user', 'root')
    mysql_password = database_config.get('mysql_password', '')
    mysql_database = database_config.get('mysql_database', 'bandix_monitor')
    mysql_charset = database_config.get('mysql_charset', 'utf8mb4')
    
    # URL编码用户名和密码（处理特殊字符如@, :, /等）
    encoded_user = quote_plus(str(mysql_user))
    encoded_password = quote_plus(str(mysql_password))
    
    # 生成MySQL URI: mysql+pymysql://user:password@host:port/database?charset=charset
    database_uri = f"mysql+pymysql://{encoded_user}:{encoded_password}@{mysql_host}:{mysql_port}/{mysql_database}?charset={mysql_charset}"
    return database_uri, None


def get_traffic_database_uri(database_config: Optional[Dict] = None) -> Tuple[str, str]:
    """
    获取流量数据库的URI（使用bind_key='traffic'）
    
    Args:
        database_config: 数据库配置字典，如果为None则从配置文件读取
        
    Returns:
        tuple: (database_uri, bind_key)
            - database_uri: SQLAlchemy数据库URI
            - bind_key: 绑定键（'traffic'）
    """
    if database_config is None:
        database_config = get_database_config()
    
    mysql_host = database_config.get('mysql_host', 'localhost')
    mysql_port = database_config.get('mysql_port', '3306')
    mysql_user = database_config.get('mysql_user', 'root')
    mysql_password = database_config.get('mysql_password', '')
    mysql_database = database_config.get('mysql_database', 'bandix_monitor')
    mysql_charset = database_config.get('mysql_charset', 'utf8mb4')
    
    # URL编码用户名和密码（处理特殊字符如@, :, /等）
    encoded_user = quote_plus(str(mysql_user))
    encoded_password = quote_plus(str(mysql_password))
    
    # MySQL使用相同的数据库，但可以通过不同的表前缀区分
    # 或者使用不同的数据库名称
    traffic_database = database_config.get('mysql_traffic_database', mysql_database)
    database_uri = f"mysql+pymysql://{encoded_user}:{encoded_password}@{mysql_host}:{mysql_port}/{traffic_database}?charset={mysql_charset}"
    return database_uri, 'traffic'


def validate_mysql_connection(database_config: Dict) -> Tuple[bool, Optional[str]]:
    """
    验证MySQL连接
    
    Args:
        database_config: 数据库配置字典（必须包含MySQL连接信息）
        
    Returns:
        tuple: (is_valid, error_message)
            - is_valid: 连接是否成功
            - error_message: 错误信息（如果连接失败）
    """
    # 首先尝试导入pymysql
    try:
        import pymysql
    except ImportError as e:
        import sys
        python_exe = sys.executable
        return False, f"pymysql模块未安装（Python路径: {python_exe}），请运行: pip install pymysql。错误: {str(e)}"
    except Exception as e:
        import sys
        python_exe = sys.executable
        return False, f"导入pymysql时发生错误（Python路径: {python_exe}）: {str(e)}"
    
    try:
        mysql_host = database_config.get('mysql_host', 'localhost')
        mysql_port = int(database_config.get('mysql_port', '3306'))
        mysql_user = database_config.get('mysql_user', 'root')
        mysql_password = database_config.get('mysql_password', '')
        mysql_database = database_config.get('mysql_database', 'bandix_monitor')
        mysql_charset = database_config.get('mysql_charset', 'utf8mb4')
        
        # 尝试连接MySQL（不指定数据库，先测试连接）
        try:
            connection = pymysql.connect(
                host=mysql_host,
                port=mysql_port,
                user=mysql_user,
                password=mysql_password,
                charset=mysql_charset,
                connect_timeout=5
            )
            connection.close()
            return True, None
        except pymysql.Error as e:
            return False, f"MySQL连接失败: {str(e)}"
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        return False, f"验证MySQL连接时发生错误: {error_msg}"


def validate_database_config(database_config: Dict) -> Tuple[bool, Optional[str]]:
    """
    验证MySQL数据库配置的有效性
    
    Args:
        database_config: 数据库配置字典
        
    Returns:
        tuple: (is_valid, error_message)
            - is_valid: 配置是否有效
            - error_message: 错误信息（如果配置无效）
    """
    errors = []
    
    # 验证MySQL配置
    mysql_host = database_config.get('mysql_host', '').strip()
    if not mysql_host:
        errors.append("database.mysql_host不能为空")
    
    mysql_port = database_config.get('mysql_port', '3306')
    try:
        port_num = int(mysql_port)
        if port_num < 1 or port_num > 65535:
            errors.append("database.mysql_port必须在1-65535范围内")
    except ValueError:
        errors.append("database.mysql_port必须是有效的数字")
    
    mysql_user = database_config.get('mysql_user', '').strip()
    if not mysql_user:
        errors.append("database.mysql_user不能为空")
    
    mysql_database = database_config.get('mysql_database', '').strip()
    if not mysql_database:
        errors.append("database.mysql_database不能为空")
    
    mysql_charset = database_config.get('mysql_charset', 'utf8mb4').strip()
    if not mysql_charset:
        errors.append("database.mysql_charset不能为空")
    
    if errors:
        return False, "; ".join(errors)
    
    return True, None

