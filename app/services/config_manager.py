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
        tuple: (bandix_config, api_config, collector_config, notifications_config, backup_config, report_config, logging_config, database_config)
    """
    if config_file_path is None:
        config_file_path = get_config_file_path()
    
    if not os.path.exists(config_file_path):
        return {}, {}, {}, {}, {}, {}, {}, {}
    
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
    
    notifications_config = {}
    if "notifications" in config:
        notifications_config = dict(config["notifications"])
    
    backup_config = {}
    if "backup" in config:
        backup_config = dict(config["backup"])
    
    report_config = {}
    if "report" in config:
        report_config = dict(config["report"])
    
    logging_config = {}
    if "logging" in config:
        logging_config = dict(config["logging"])
    
    database_config = {}
    if "database" in config:
        database_config = dict(config["database"])
    
    return bandix_config, api_config, collector_config, notifications_config, backup_config, report_config, logging_config, database_config


def save_config_file(bandix_config=None, api_config=None, collector_config=None, notifications_config=None, backup_config=None, report_config=None, logging_config=None, database_config=None, config_file_path=None):
    """
    保存配置文件
    
    Args:
        bandix_config: bandix配置字典（可选，如果提供则完全替换）
        api_config: api配置字典（可选，如果提供则完全替换）
        collector_config: collector配置字典（可选，如果提供则完全替换）
        notifications_config: notifications配置字典（可选，如果提供则完全替换）
        backup_config: backup配置字典（可选，如果提供则完全替换）
        report_config: report配置字典（可选，如果提供则完全替换）
        logging_config: logging配置字典（可选，如果提供则完全替换）
        database_config: database配置字典（可选，如果提供则完全替换）
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
        
        if notifications_config is not None:
            if "notifications" not in config:
                config.add_section("notifications")
            for key, value in notifications_config.items():
                config.set("notifications", key, str(value))
        
        if backup_config is not None:
            if "backup" not in config:
                config.add_section("backup")
            for key, value in backup_config.items():
                config.set("backup", key, str(value))
        
        if report_config is not None:
            if "report" not in config:
                config.add_section("report")
            for key, value in report_config.items():
                config.set("report", key, str(value))
        
        if logging_config is not None:
            if "logging" not in config:
                config.add_section("logging")
            for key, value in logging_config.items():
                config.set("logging", key, str(value))
        
        if database_config is not None:
            if "database" not in config:
                config.add_section("database")
            for key, value in database_config.items():
                config.set("database", key, str(value))
        
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


def validate_config(bandix_config=None, api_config=None, collector_config=None, notifications_config=None, backup_config=None, report_config=None, logging_config=None):
    """
    验证配置的有效性
    
    Args:
        bandix_config: bandix配置字典（可选）
        api_config: api配置字典（可选）
        collector_config: collector配置字典（可选）
        notifications_config: notifications配置字典（可选）
        backup_config: backup配置字典（可选）
        report_config: report配置字典（可选）
        logging_config: logging配置字典（可选）
        
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
    
    # 验证notifications配置
    if notifications_config:
        email_enabled = notifications_config.get('email_enabled', 'false').lower()
        if email_enabled == 'true':
            if not notifications_config.get('email_smtp_host', '').strip():
                errors.append("notifications.email_smtp_host不能为空（邮件通知已启用）")
            if not notifications_config.get('email_username', '').strip():
                errors.append("notifications.email_username不能为空（邮件通知已启用）")
            if not notifications_config.get('email_from', '').strip():
                errors.append("notifications.email_from不能为空（邮件通知已启用）")
            if not notifications_config.get('email_to', '').strip():
                errors.append("notifications.email_to不能为空（邮件通知已启用）")
            
            smtp_port = notifications_config.get('email_smtp_port', '587')
            try:
                port_num = int(smtp_port)
                if port_num < 1 or port_num > 65535:
                    errors.append("notifications.email_smtp_port必须在1-65535范围内")
            except ValueError:
                errors.append("notifications.email_smtp_port必须是有效的数字")
        
        webhook_enabled = notifications_config.get('webhook_enabled', 'false').lower()
        if webhook_enabled == 'true':
            if not notifications_config.get('webhook_urls', '').strip():
                errors.append("notifications.webhook_urls不能为空（Webhook通知已启用）")
        
        telegram_enabled = notifications_config.get('telegram_enabled', 'false').lower()
        if telegram_enabled == 'true':
            if not notifications_config.get('telegram_bot_token', '').strip():
                errors.append("notifications.telegram_bot_token不能为空（Telegram通知已启用）")
            if not notifications_config.get('telegram_chat_ids', '').strip():
                errors.append("notifications.telegram_chat_ids不能为空（Telegram通知已启用）")
        
        wecom_enabled = notifications_config.get('wecom_enabled', 'false').lower()
        if wecom_enabled == 'true':
            if not notifications_config.get('wecom_webhook_urls', '').strip():
                errors.append("notifications.wecom_webhook_urls不能为空（企业微信通知已启用）")
        
        dingtalk_enabled = notifications_config.get('dingtalk_enabled', 'false').lower()
        if dingtalk_enabled == 'true':
            if not notifications_config.get('dingtalk_webhook_urls', '').strip():
                errors.append("notifications.dingtalk_webhook_urls不能为空（钉钉通知已启用）")
    
    # 验证report配置
    if report_config:
        report_enabled = report_config.get('report_enabled', 'false').lower()
        if report_enabled == 'true':
            # 验证时间格式
            for time_key in ['daily_time', 'weekly_time', 'monthly_time']:
                time_value = report_config.get(time_key, '')
                if time_value:
                    # 去除注释
                    if '#' in time_value:
                        time_value = time_value.split('#')[0]
                    time_value = time_value.strip()
                    # 验证时间格式 HH:MM
                    try:
                        parts = time_value.split(':')
                        if len(parts) != 2:
                            raise ValueError
                        hour = int(parts[0])
                        minute = int(parts[1])
                        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                            errors.append(f"report.{time_key}时间格式无效（应为HH:MM）")
                    except:
                        errors.append(f"report.{time_key}时间格式无效（应为HH:MM）")
            
            # 验证keep_count
            keep_count_str = report_config.get('keep_count', '30')
            if '#' in keep_count_str:
                keep_count_str = keep_count_str.split('#')[0]
            try:
                keep_count = int(keep_count_str.strip())
                if keep_count < 1:
                    errors.append("report.keep_count必须大于0")
            except ValueError:
                errors.append("report.keep_count必须是有效的数字")
            
            # 验证邮件配置（如果启用）
            email_enabled = report_config.get('email_enabled', 'false').lower()
            if email_enabled == 'true':
                if not report_config.get('email_recipients', '').strip():
                    errors.append("report.email_recipients不能为空（邮件发送已启用）")
    
    # 验证logging配置
    if logging_config:
        log_level = logging_config.get('log_level', 'INFO').upper()
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if log_level not in valid_levels:
            errors.append(f"logging.log_level必须是以下之一: {', '.join(valid_levels)}")
        
        log_format = logging_config.get('log_format', 'both').lower()
        if log_format not in ['json', 'text', 'both']:
            errors.append("logging.log_format必须是: json, text, 或 both")
        
        log_max_bytes = logging_config.get('log_max_bytes', '10')
        try:
            max_bytes = int(log_max_bytes)
            if max_bytes < 1:
                errors.append("logging.log_max_bytes必须大于0")
        except ValueError:
            errors.append("logging.log_max_bytes必须是有效的数字")
        
        log_backup_count = logging_config.get('log_backup_count', '30')
        try:
            backup_count = int(log_backup_count)
            if backup_count < 1:
                errors.append("logging.log_backup_count必须大于0")
        except ValueError:
            errors.append("logging.log_backup_count必须是有效的数字")
        
        log_rotation = logging_config.get('log_rotation', 'both').lower()
        if log_rotation not in ['size', 'time', 'both']:
            errors.append("logging.log_rotation必须是: size, time, 或 both")
    
    if errors:
        return False, "; ".join(errors)
    
    return True, None

