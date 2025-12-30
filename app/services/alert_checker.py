#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
告警检查服务
检查流量阈值和设备离线告警
"""
from datetime import datetime, timedelta
from sqlalchemy import desc, func
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.models.user_models import db
from app.models.alert_models import AlertRule, AlertHistory
from app.models.database_models import Device, TotalTraffic, DeviceTraffic


def check_traffic_threshold_alerts(app):
    """
    检查流量阈值告警
    
    Args:
        app: Flask应用实例（用于应用上下文）
    """
    # 注意：此函数应该在app.app_context()中调用
    try:
        # 获取所有启用的流量阈值告警规则
        rules = AlertRule.query.filter(
            AlertRule.enabled == True,
            AlertRule.type == 'traffic_threshold'
        ).all()
        
        if not rules:
            return
        
        # 获取最新的全网流量数据
        latest_total = TotalTraffic.query.order_by(desc(TotalTraffic.timestamp)).first()
        
        for rule in rules:
            try:
                # 检查是否有该规则的活跃告警（避免重复告警）
                recent_alert = AlertHistory.query.filter(
                    AlertHistory.rule_id == rule.id,
                    AlertHistory.status == 'triggered',
                    AlertHistory.triggered_at >= datetime.utcnow() - timedelta(minutes=5)
                ).first()
                
                if recent_alert:
                    # 最近5分钟内已有告警，跳过
                    continue
                
                threshold = rule.threshold_bytes
                triggered = False
                message = ""
                device_id = None
                
                if rule.device_id:
                    # 检查特定设备的流量
                    latest_device_traffic = DeviceTraffic.query.filter(
                        DeviceTraffic.device_id == rule.device_id
                    ).order_by(desc(DeviceTraffic.timestamp)).first()
                    
                    if latest_device_traffic:
                        # 计算总流量速率（下行+上行）
                        total_speed = latest_device_traffic.down_speed_bytes + latest_device_traffic.up_speed_bytes
                        
                        if total_speed >= threshold:
                            triggered = True
                            device = Device.query.get(rule.device_id)
                            device_name = device.hostname if device and device.hostname else device.mac if device else f"设备{rule.device_id}"
                            message = f"设备 {device_name} 流量超过阈值: {format_bytes(total_speed)} >= {format_bytes(threshold)}"
                            device_id = rule.device_id
                else:
                    # 检查全网流量
                    if latest_total:
                        total_speed = latest_total.down_speed_bytes + latest_total.up_speed_bytes
                        
                        if total_speed >= threshold:
                            triggered = True
                            message = f"全网流量超过阈值: {format_bytes(total_speed)} >= {format_bytes(threshold)}"
                
                if triggered:
                    # 创建告警历史记录
                    alert = AlertHistory(
                        rule_id=rule.id,
                        alert_type='traffic_threshold',
                        message=message,
                        severity=rule.severity,
                        status='triggered',
                        device_id=device_id,
                        triggered_at=datetime.utcnow()
                    )
                    db.session.add(alert)
                    db.session.commit()
                    
                    print(f"[告警检查] 触发流量阈值告警: {message}")
                    
            except Exception as e:
                print(f"[告警检查] 检查规则 {rule.id} 时出错: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                db.session.rollback()
                continue
                
    except Exception as e:
        print(f"[告警检查] 检查流量阈值告警时出错: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        db.session.rollback()


def check_device_offline_alerts(app):
    """
    检查设备离线告警
    
    Args:
        app: Flask应用实例（用于应用上下文）
    """
    # 注意：此函数应该在app.app_context()中调用
    try:
        # 获取所有启用的设备离线告警规则
        rules = AlertRule.query.filter(
            AlertRule.enabled == True,
            AlertRule.type == 'device_offline'
        ).all()
        
        if not rules:
            return
        
        # 获取所有设备的最后活动时间
        devices = Device.query.all()
        
        for rule in rules:
            try:
                offline_threshold_minutes = rule.offline_threshold_minutes
                if not offline_threshold_minutes or offline_threshold_minutes <= 0:
                    continue
                
                threshold_time = datetime.utcnow() - timedelta(minutes=offline_threshold_minutes)
                
                for device in devices:
                    # 检查是否有该设备该规则的活跃告警
                    recent_alert = AlertHistory.query.filter(
                        AlertHistory.rule_id == rule.id,
                        AlertHistory.device_id == device.id,
                        AlertHistory.status == 'triggered',
                        AlertHistory.triggered_at >= datetime.utcnow() - timedelta(minutes=5)
                    ).first()
                    
                    if recent_alert:
                        # 最近5分钟内已有告警，跳过
                        continue
                    
                    # 获取设备最后活动时间
                    latest_traffic = DeviceTraffic.query.filter(
                        DeviceTraffic.device_id == device.id
                    ).order_by(desc(DeviceTraffic.timestamp)).first()
                    
                    if not latest_traffic:
                        # 设备从未有流量数据，跳过
                        continue
                    
                    last_active_time = latest_traffic.timestamp
                    
                    if last_active_time < threshold_time:
                        # 设备离线
                        device_name = device.hostname if device.hostname else device.mac
                        message = f"设备 {device_name} 离线超过 {offline_threshold_minutes} 分钟（最后活动: {last_active_time.strftime('%Y-%m-%d %H:%M:%S')}）"
                        
                        # 创建告警历史记录
                        alert = AlertHistory(
                            rule_id=rule.id,
                            alert_type='device_offline',
                            message=message,
                            severity=rule.severity,
                            status='triggered',
                            device_id=device.id,
                            triggered_at=datetime.utcnow()
                        )
                        db.session.add(alert)
                        db.session.commit()
                        
                        print(f"[告警检查] 触发设备离线告警: {message}")
                        
            except Exception as e:
                print(f"[告警检查] 检查规则 {rule.id} 时出错: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                db.session.rollback()
                continue
                
    except Exception as e:
        print(f"[告警检查] 检查设备离线告警时出错: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        db.session.rollback()


def check_alerts(app):
    """
    主检查函数，调用所有告警检查
    
    Args:
        app: Flask应用实例（用于应用上下文）
    """
    try:
        # 确保在应用上下文中执行
        with app.app_context():
            check_traffic_threshold_alerts(app)
            check_device_offline_alerts(app)
    except Exception as e:
        print(f"[告警检查] 执行告警检查时出错: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


def format_bytes(bytes_value):
    """
    格式化字节数为可读字符串
    
    Args:
        bytes_value: 字节数
        
    Returns:
        str: 格式化后的字符串（如 "1.23 MB"）
    """
    if bytes_value < 1024:
        return f"{bytes_value} B"
    elif bytes_value < 1024 * 1024:
        return f"{bytes_value / 1024:.2f} KB"
    elif bytes_value < 1024 * 1024 * 1024:
        return f"{bytes_value / (1024 * 1024):.2f} MB"
    else:
        return f"{bytes_value / (1024 * 1024 * 1024):.2f} GB"

