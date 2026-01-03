#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知服务
支持多种通知渠道：邮件、Webhook、Telegram等
"""
import os
import sys
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.services.config_manager import load_config_file, get_config_file_path


class NotificationChannel:
    """通知渠道基类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化通知渠道
        
        Args:
            config: 渠道配置字典
        """
        self.config = config
        self.enabled = config.get('enabled', 'false').lower() == 'true'
    
    def is_enabled(self) -> bool:
        """检查渠道是否启用"""
        return self.enabled
    
    def send(self, message: str, subject: str = None, **kwargs) -> Tuple[bool, str]:
        """
        发送通知
        
        Args:
            message: 消息内容
            subject: 主题（如果适用）
            **kwargs: 其他参数
            
        Returns:
            tuple: (success, error_message)
        """
        raise NotImplementedError("子类必须实现 send 方法")


class EmailNotificationChannel(NotificationChannel):
    """邮件通知渠道"""
    
    def send(self, message: str, subject: str = None, **kwargs) -> Tuple[bool, str]:
        """发送邮件"""
        if not self.is_enabled():
            return False, "邮件通知未启用"
        
        try:
            smtp_host = self.config.get('smtp_host', '').strip()
            smtp_port = int(self.config.get('smtp_port', '587'))
            use_tls = self.config.get('use_tls', 'true').lower() == 'true'
            username = self.config.get('username', '').strip()
            password = self.config.get('password', '').strip()
            from_addr = self.config.get('from', '').strip()
            to_addrs = self.config.get('to', '').strip()
            
            if not all([smtp_host, username, password, from_addr, to_addrs]):
                return False, "邮件配置不完整"
            
            # 解析收件人列表（支持多个，用分号或逗号分隔）
            to_list = [addr.strip() for addr in to_addrs.replace(';', ',').split(',') if addr.strip()]
            if not to_list:
                return False, "收件人地址不能为空"
            
            # 创建邮件消息
            msg = MIMEMultipart('alternative')
            msg['From'] = from_addr
            msg['To'] = ', '.join(to_list)
            msg['Subject'] = subject or 'Bandix Monitor 告警通知'
            
            # 添加HTML内容
            html_part = MIMEText(message, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 发送邮件
            # 465端口使用SSL，587端口使用TLS
            if smtp_port == 465:
                # 465端口使用SSL
                with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as server:
                    server.login(username, password)
                    server.sendmail(from_addr, to_list, msg.as_string())
            else:
                # 其他端口（如587）使用TLS
                with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                    if use_tls:
                        server.starttls()
                    server.login(username, password)
                    server.sendmail(from_addr, to_list, msg.as_string())
            
            return True, "邮件发送成功"
            
        except smtplib.SMTPException as e:
            return False, f"SMTP错误: {str(e)}"
        except Exception as e:
            return False, f"发送邮件失败: {str(e)}"


class WebhookNotificationChannel(NotificationChannel):
    """Webhook 通知渠道"""
    
    def send(self, message: str, subject: str = None, **kwargs) -> Tuple[bool, str]:
        """发送 Webhook 请求"""
        if not self.is_enabled():
            return False, "Webhook通知未启用"
        
        try:
            urls = self.config.get('urls', '').strip()
            headers_str = self.config.get('headers', '{}').strip()
            
            if not urls:
                return False, "Webhook URL不能为空"
            
            # 解析URL列表（支持多个，用分号或逗号分隔）
            url_list = [url.strip() for url in urls.replace(';', ',').split(',') if url.strip()]
            if not url_list:
                return False, "Webhook URL列表不能为空"
            
            # 解析请求头
            try:
                headers = json.loads(headers_str) if headers_str else {}
            except json.JSONDecodeError:
                headers = {}
            
            # 构建请求体
            payload = {
                'message': message,
                'subject': subject,
                'timestamp': datetime.utcnow().isoformat(),
                **kwargs
            }
            
            # 发送到所有URL
            errors = []
            success_count = 0
            
            for url in url_list:
                try:
                    response = requests.post(
                        url,
                        json=payload,
                        headers=headers,
                        timeout=10
                    )
                    response.raise_for_status()
                    success_count += 1
                except requests.RequestException as e:
                    errors.append(f"{url}: {str(e)}")
            
            if success_count == len(url_list):
                return True, f"所有Webhook发送成功（{success_count}个）"
            elif success_count > 0:
                return False, f"部分Webhook发送失败: {', '.join(errors)}"
            else:
                return False, f"所有Webhook发送失败: {', '.join(errors)}"
                
        except Exception as e:
            return False, f"发送Webhook失败: {str(e)}"


class TelegramNotificationChannel(NotificationChannel):
    """Telegram Bot 通知渠道"""
    
    def send(self, message: str, subject: str = None, **kwargs) -> Tuple[bool, str]:
        """发送 Telegram 消息"""
        if not self.is_enabled():
            return False, "Telegram通知未启用"
        
        try:
            bot_token = self.config.get('bot_token', '').strip()
            chat_ids_str = self.config.get('chat_ids', '').strip()
            
            if not bot_token:
                return False, "Telegram Bot Token不能为空"
            
            if not chat_ids_str:
                return False, "Telegram Chat IDs不能为空"
            
            # 解析Chat ID列表（支持多个，用分号或逗号分隔）
            chat_ids = [cid.strip() for cid in chat_ids_str.replace(';', ',').split(',') if cid.strip()]
            if not chat_ids:
                return False, "Chat ID列表不能为空"
            
            # 构建消息内容
            full_message = f"*{subject or 'Bandix Monitor 告警'}*\n\n{message}"
            
            # 发送到所有Chat
            errors = []
            success_count = 0
            
            api_base_url = f"https://api.telegram.org/bot{bot_token}"
            
            for chat_id in chat_ids:
                try:
                    response = requests.post(
                        f"{api_base_url}/sendMessage",
                        json={
                            'chat_id': chat_id,
                            'text': full_message,
                            'parse_mode': 'Markdown'
                        },
                        timeout=10
                    )
                    response.raise_for_status()
                    success_count += 1
                except requests.RequestException as e:
                    errors.append(f"Chat {chat_id}: {str(e)}")
            
            if success_count == len(chat_ids):
                return True, f"所有Telegram消息发送成功（{success_count}个）"
            elif success_count > 0:
                return False, f"部分Telegram消息发送失败: {', '.join(errors)}"
            else:
                return False, f"所有Telegram消息发送失败: {', '.join(errors)}"
                
        except Exception as e:
            return False, f"发送Telegram消息失败: {str(e)}"


class WeComNotificationChannel(NotificationChannel):
    """企业微信机器人通知渠道"""
    
    def send(self, message: str, subject: str = None, **kwargs) -> Tuple[bool, str]:
        """发送企业微信消息"""
        if not self.is_enabled():
            return False, "企业微信通知未启用"
        
        try:
            webhook_urls = self.config.get('webhook_urls', '').strip()
            
            if not webhook_urls:
                return False, "企业微信 Webhook URL不能为空"
            
            # 解析URL列表（支持多个，用分号或逗号分隔）
            url_list = [url.strip() for url in webhook_urls.replace(';', ',').split(',') if url.strip()]
            if not url_list:
                return False, "企业微信 Webhook URL列表不能为空"
            
            # 构建 Markdown 消息内容
            markdown_content = f"## {subject or 'Bandix Monitor 告警'}\n\n{message}"
            
            # 构建请求体（企业微信格式）
            payload = {
                'msgtype': 'markdown',
                'markdown': {
                    'content': markdown_content
                }
            }
            
            # 发送到所有URL
            errors = []
            success_count = 0
            
            for url in url_list:
                try:
                    response = requests.post(
                        url,
                        json=payload,
                        timeout=10
                    )
                    response.raise_for_status()
                    result = response.json()
                    # 企业微信返回 {"errcode": 0, "errmsg": "ok"} 表示成功
                    if result.get('errcode') == 0:
                        success_count += 1
                    else:
                        errors.append(f"{url}: {result.get('errmsg', '未知错误')}")
                except requests.RequestException as e:
                    errors.append(f"{url}: {str(e)}")
            
            if success_count == len(url_list):
                return True, f"所有企业微信消息发送成功（{success_count}个）"
            elif success_count > 0:
                return False, f"部分企业微信消息发送失败: {', '.join(errors)}"
            else:
                return False, f"所有企业微信消息发送失败: {', '.join(errors)}"
                
        except Exception as e:
            return False, f"发送企业微信消息失败: {str(e)}"


class DingTalkNotificationChannel(NotificationChannel):
    """钉钉机器人通知渠道"""
    
    def send(self, message: str, subject: str = None, **kwargs) -> Tuple[bool, str]:
        """发送钉钉消息"""
        if not self.is_enabled():
            return False, "钉钉通知未启用"
        
        try:
            webhook_urls = self.config.get('webhook_urls', '').strip()
            
            if not webhook_urls:
                return False, "钉钉 Webhook URL不能为空"
            
            # 解析URL列表（支持多个，用分号或逗号分隔）
            url_list = [url.strip() for url in webhook_urls.replace(';', ',').split(',') if url.strip()]
            if not url_list:
                return False, "钉钉 Webhook URL列表不能为空"
            
            # 构建 Markdown 消息内容
            markdown_title = subject or 'Bandix Monitor 告警'
            markdown_text = message
            
            # 构建请求体（钉钉格式）
            payload = {
                'msgtype': 'markdown',
                'markdown': {
                    'title': markdown_title,
                    'text': markdown_text
                }
            }
            
            # 发送到所有URL
            errors = []
            success_count = 0
            
            for url in url_list:
                try:
                    response = requests.post(
                        url,
                        json=payload,
                        timeout=10
                    )
                    response.raise_for_status()
                    result = response.json()
                    # 钉钉返回 {"errcode": 0, "errmsg": "ok"} 表示成功
                    if result.get('errcode') == 0:
                        success_count += 1
                    else:
                        errors.append(f"{url}: {result.get('errmsg', '未知错误')}")
                except requests.RequestException as e:
                    errors.append(f"{url}: {str(e)}")
            
            if success_count == len(url_list):
                return True, f"所有钉钉消息发送成功（{success_count}个）"
            elif success_count > 0:
                return False, f"部分钉钉消息发送失败: {', '.join(errors)}"
            else:
                return False, f"所有钉钉消息发送失败: {', '.join(errors)}"
                
        except Exception as e:
            return False, f"发送钉钉消息失败: {str(e)}"


class PageNotificationChannel(NotificationChannel):
    """页面通知渠道（已存在，无需实际发送，仅用于标记）"""
    
    def send(self, message: str, subject: str = None, **kwargs) -> Tuple[bool, str]:
        """页面通知无需实际发送，告警记录已保存到数据库"""
        return True, "页面通知已记录"


class NotificationService:
    """通知服务，统一管理所有通知渠道"""
    
    def __init__(self):
        """初始化通知服务"""
        self.channels = {}
        self._load_config()
    
    def _load_config(self):
        """从配置文件加载通知配置"""
        try:
            config_file = get_config_file_path()
            _, _, _, notifications_config, _, _, _ = load_config_file(config_file)
            
            # 邮件配置
            email_config = {
                'enabled': notifications_config.get('email_enabled', 'false'),
                'smtp_host': notifications_config.get('email_smtp_host', ''),
                'smtp_port': notifications_config.get('email_smtp_port', '587'),
                'use_tls': notifications_config.get('email_use_tls', 'true'),
                'username': notifications_config.get('email_username', ''),
                'password': notifications_config.get('email_password', ''),
                'from': notifications_config.get('email_from', ''),
                'to': notifications_config.get('email_to', ''),
            }
            self.channels['email'] = EmailNotificationChannel(email_config)
            
            # Webhook配置
            webhook_config = {
                'enabled': notifications_config.get('webhook_enabled', 'false'),
                'urls': notifications_config.get('webhook_urls', ''),
                'headers': notifications_config.get('webhook_headers', '{}'),
            }
            self.channels['webhook'] = WebhookNotificationChannel(webhook_config)
            
            # Telegram配置
            telegram_config = {
                'enabled': notifications_config.get('telegram_enabled', 'false'),
                'bot_token': notifications_config.get('telegram_bot_token', ''),
                'chat_ids': notifications_config.get('telegram_chat_ids', ''),
            }
            self.channels['telegram'] = TelegramNotificationChannel(telegram_config)
            
            # 企业微信配置
            wecom_config = {
                'enabled': notifications_config.get('wecom_enabled', 'false'),
                'webhook_urls': notifications_config.get('wecom_webhook_urls', ''),
            }
            self.channels['wecom'] = WeComNotificationChannel(wecom_config)
            
            # 钉钉配置
            dingtalk_config = {
                'enabled': notifications_config.get('dingtalk_enabled', 'false'),
                'webhook_urls': notifications_config.get('dingtalk_webhook_urls', ''),
            }
            self.channels['dingtalk'] = DingTalkNotificationChannel(dingtalk_config)
            
            # 页面通知（总是可用）
            self.channels['page'] = PageNotificationChannel({'enabled': 'true'})
            
        except Exception as e:
            print(f"[通知服务] 加载配置失败: {e}", file=sys.stderr)
            # 即使配置加载失败，也要提供页面通知渠道
            self.channels['page'] = PageNotificationChannel({'enabled': 'true'})
    
    def reload_config(self):
        """重新加载配置"""
        self.channels.clear()
        self._load_config()
    
    def format_alert_message(self, alert_history: Dict[str, Any], format_type: str = 'html') -> str:
        """
        格式化告警消息
        
        Args:
            alert_history: 告警历史记录字典
            format_type: 格式类型 ('html' 或 'text')
            
        Returns:
            str: 格式化后的消息
        """
        severity_map = {
            'critical': '严重',
            'warning': '警告',
            'info': '信息'
        }
        
        alert_type_map = {
            'traffic_threshold': '流量阈值告警',
            'device_offline': '设备离线告警'
        }
        
        severity = alert_history.get('severity', 'warning')
        alert_type = alert_history.get('alert_type', '')
        message = alert_history.get('message', '')
        triggered_at = alert_history.get('triggered_at', '')
        
        if format_type == 'html':
            severity_color = {
                'critical': '#dc3545',
                'warning': '#ffc107',
                'info': '#17a2b8'
            }.get(severity, '#666')
            
            html = f"""
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .alert-box {{ border-left: 4px solid {severity_color}; padding: 15px; background-color: #f8f9fa; margin: 10px 0; }}
                    .severity {{ color: {severity_color}; font-weight: bold; }}
                    .timestamp {{ color: #666; font-size: 0.9em; }}
                </style>
            </head>
            <body>
                <div class="alert-box">
                    <div class="severity">[{severity_map.get(severity, severity)}] {alert_type_map.get(alert_type, alert_type)}</div>
                    <div style="margin-top: 10px;">{message}</div>
                    <div class="timestamp" style="margin-top: 10px;">触发时间: {triggered_at}</div>
                </div>
            </body>
            </html>
            """
            return html
        else:
            # 纯文本格式
            text = f"""
[{severity_map.get(severity, severity)}] {alert_type_map.get(alert_type, alert_type)}

{message}

触发时间: {triggered_at}
            """
            return text.strip()
    
    def format_alert_message_markdown(self, alert_history: Dict[str, Any]) -> str:
        """
        格式化告警消息为 Markdown 格式（用于企业微信和钉钉）
        
        Args:
            alert_history: 告警历史记录字典
            
        Returns:
            str: Markdown 格式的消息
        """
        severity_map = {
            'critical': '严重',
            'warning': '警告',
            'info': '信息'
        }
        
        alert_type_map = {
            'traffic_threshold': '流量阈值告警',
            'device_offline': '设备离线告警'
        }
        
        severity = alert_history.get('severity', 'warning')
        alert_type = alert_history.get('alert_type', '')
        message = alert_history.get('message', '')
        triggered_at = alert_history.get('triggered_at', '')
        
        # Markdown 格式
        markdown = f"""## [{severity_map.get(severity, severity)}] {alert_type_map.get(alert_type, alert_type)}

{message}

**触发时间**: {triggered_at}
"""
        return markdown.strip()
    
    def send_notification(self, notification_methods: List[str], alert_history: Dict[str, Any]) -> Dict[str, Tuple[bool, str]]:
        """
        发送通知到指定的通知渠道
        
        Args:
            notification_methods: 通知方式列表，如 ['page', 'email', 'webhook']
            alert_history: 告警历史记录字典
            
        Returns:
            Dict[str, tuple[bool, str]]: 各渠道发送结果 {channel: (success, message)}
        """
        results = {}
        
        # 格式化消息
        subject = f"Bandix Monitor 告警 - {alert_history.get('alert_type', 'Unknown')}"
        html_message = self.format_alert_message(alert_history, 'html')
        text_message = self.format_alert_message(alert_history, 'text')
        
        # 发送到每个指定的渠道
        for method in notification_methods:
            if method not in self.channels:
                results[method] = (False, f"不支持的通知渠道: {method}")
                continue
            
            channel = self.channels[method]
            
            # 根据渠道类型选择消息格式
            if isinstance(channel, EmailNotificationChannel):
                message = html_message
            elif isinstance(channel, (WeComNotificationChannel, DingTalkNotificationChannel)):
                # 企业微信和钉钉使用 Markdown 格式
                message = self.format_alert_message_markdown(alert_history)
            elif isinstance(channel, TelegramNotificationChannel):
                message = text_message
            else:
                message = text_message
            
            success, msg = channel.send(message, subject, alert_history=alert_history)
            results[method] = (success, msg)
        
        return results

