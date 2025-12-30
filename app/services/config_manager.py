#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件管理工具
提供配置文件的读取、更新和保存功能
"""
import os
import sys
import configparser
import shutil
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def get_config_file_path():
    """
    获取配置文件路径
    """
    config_file = os.getenv("BANDIX_CONFIG")
    if not config_file:
        config_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "app",
            "config",
            "bandix_config.ini"
        )
    return config_file


def load_config_file(config_file_path=None):
    """
    读取配置文件
    
    Args:
        config_file_path: 配置文件路径（如果为None，则使用默认路径）
        
    Returns:
        tuple: (bandix_config, api_config, collector_config)
    """
    if config_file_path is None:
        config_file_path = get_config_file_path()
    
    if not os.path.exists(config_file_path):
        return {}, {}, {}
    
    config = configparser.ConfigParser()
    try:
        config.read(config_file_path, encoding='utf-8')
    except Exception as e:
        raise Exception(f"无法读取配置文件: {e}")
    
    bandix_config = {}
    if "bandix" in config:
        bandix_config = dict(config["bandix"])
    
    api_config = {}
    if "api" in config:
        api_config = dict(config["api"])
    
    collector_config = {}
    if "collector" in config:
        collector_config = dict(config["collector"])
    
    return bandix_config, api_config, collector_config


def save_config_file(bandix_config=None, api_config=None, collector_config=None, config_file_path=None):
    """
    保存配置文件
    
    Args:
        bandix_config: bandix配置字典（可选，如果提供则完全替换）
        api_config: api配置字典（可选，如果提供则完全替换）
        collector_config: collector配置字典（可选，如果提供则完全替换）
        config_file_path: 配置文件路径（如果为None，则使用默认路径）
        
    Returns:
        bool: 是否保存成功
    """
    if config_file_path is None:
        config_file_path = get_config_file_path()
    
    try:
        # 先备份原配置文件
        if os.path.exists(config_file_path):
            backup_path = f"{config_file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(config_file_path, backup_path)
        
        # 读取现有配置
        config = configparser.ConfigParser()
        if os.path.exists(config_file_path):
            config.read(config_file_path, encoding='utf-8')
        
        # 更新配置（如果提供了新的配置，则完全替换对应section）
        if bandix_config is not None:
            if "bandix" not in config:
                config.add_section("bandix")
            for key, value in bandix_config.items():
                config.set("bandix", key, str(value))
        
        if api_config is not None:
            if "api" not in config:
                config.add_section("api")
            for key, value in api_config.items():
                config.set("api", key, str(value))
        
        if collector_config is not None:
            if "collector" not in config:
                config.add_section("collector")
            for key, value in collector_config.items():
                config.set("collector", key, str(value))
        
        # 保存配置文件
        with open(config_file_path, 'w', encoding='utf-8') as f:
            config.write(f)
        
        return True
    except Exception as e:
        raise Exception(f"保存配置文件失败: {e}")


def update_config_file(section, key, value, config_file_path=None):
    """
    更新单个配置项
    
    Args:
        section: 配置段名称（bandix/api/collector）
        key: 配置项名称
        value: 配置项值
        config_file_path: 配置文件路径（如果为None，则使用默认路径）
        
    Returns:
        bool: 是否更新成功
    """
    if config_file_path is None:
        config_file_path = get_config_file_path()
    
    try:
        config = configparser.ConfigParser()
        if os.path.exists(config_file_path):
            config.read(config_file_path, encoding='utf-8')
        
        if section not in config:
            config.add_section(section)
        
        config.set(section, key, str(value))
        
        with open(config_file_path, 'w', encoding='utf-8') as f:
            config.write(f)
        
        return True
    except Exception as e:
        raise Exception(f"更新配置项失败: {e}")


def validate_config(bandix_config=None, api_config=None, collector_config=None):
    """
    验证配置的有效性
    
    Args:
        bandix_config: bandix配置字典（可选）
        api_config: api配置字典（可选）
        collector_config: collector配置字典（可选）
        
    Returns:
        tuple: (is_valid, error_message)
    """
    errors = []
    
    # 验证bandix配置
    if bandix_config:
        url = bandix_config.get('url', '').strip()
        if url and not (url.startswith('http://') or url.startswith('https://')):
            errors.append("bandix.url必须是有效的HTTP/HTTPS URL")
        
        username = bandix_config.get('username', '').strip()
        if not username:
            errors.append("bandix.username不能为空")
    
    # 验证api配置
    if api_config:
        port = api_config.get('port', '')
        if port:
            try:
                port_num = int(port)
                if port_num < 1 or port_num > 65535:
                    errors.append("api.port必须在1-65535范围内")
            except ValueError:
                errors.append("api.port必须是有效的数字")
        
        debug = api_config.get('debug', '').lower()
        if debug and debug not in ['true', 'false', '1', '0', 'yes', 'no']:
            errors.append("api.debug必须是true/false")
        
        auth_enabled = api_config.get('auth_enabled', '').lower()
        if auth_enabled and auth_enabled not in ['true', 'false', '1', '0', 'yes', 'no']:
            errors.append("api.auth_enabled必须是true/false")
        
        health_check_require_auth = api_config.get('health_check_require_auth', '').lower()
        if health_check_require_auth and health_check_require_auth not in ['true', 'false', '1', '0', 'yes', 'no']:
            errors.append("api.health_check_require_auth必须是true/false")
    
    # 验证collector配置
    if collector_config:
        collect_interval = collector_config.get('collect_interval', '')
        if collect_interval:
            try:
                interval = float(collect_interval)
                if interval <= 0:
                    errors.append("collector.collect_interval必须大于0")
                if interval < 0.1:
                    errors.append("collector.collect_interval建议不小于0.1秒")
            except ValueError:
                errors.append("collector.collect_interval必须是有效的数字")
    
    if errors:
        return False, "; ".join(errors)
    
    return True, None

