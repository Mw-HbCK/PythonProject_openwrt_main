#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
告警数据模型
存储告警规则和历史记录
"""
from datetime import datetime
from sqlalchemy import Index
import json

# 使用user_models中的db实例，避免创建多个SQLAlchemy实例
from app.models.user_models import db


class AlertRule(db.Model):
    """
    告警规则表
    """
    __tablename__ = 'alert_rules'
    __bind_key__ = 'traffic'  # 指定使用traffic数据库
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False, index=True)  # 'traffic_threshold' or 'device_offline'
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    
    # 流量阈值告警相关字段
    threshold_bytes = db.Column(db.BigInteger, nullable=True)  # 流量阈值（字节）
    device_id = db.Column(db.Integer, nullable=True, index=True)  # 设备ID（可选，NULL表示所有设备），移除外键约束以兼容MySQL权限限制
    
    # 设备离线告警相关字段
    offline_threshold_minutes = db.Column(db.Integer, nullable=True)  # 离线阈值（分钟）
    
    # 通知方式（JSON字符串）
    notification_methods = db.Column(db.String(255), nullable=True, default='["page"]')
    
    # 严重程度（critical/warning/info）
    severity = db.Column(db.String(20), nullable=False, default='warning')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关联关系（移除外键约束后，关系定义暂时移除以避免SQLAlchemy配置错误）
    # 应用代码可以通过rule_id直接查询
    # alert_history = db.relationship('AlertHistory', backref='rule', lazy='dynamic')
    
    def __repr__(self):
        return f'<AlertRule {self.id} - {self.name}>'
    
    def to_dict(self):
        """转换为字典"""
        notification_methods_list = []
        if self.notification_methods:
            try:
                notification_methods_list = json.loads(self.notification_methods)
            except (json.JSONDecodeError, TypeError):
                notification_methods_list = ['page']
        
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'enabled': self.enabled,
            'threshold_bytes': self.threshold_bytes,
            'device_id': self.device_id,
            'offline_threshold_minutes': self.offline_threshold_minutes,
            'notification_methods': notification_methods_list,
            'severity': self.severity,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class AlertHistory(db.Model):
    """
    告警历史表
    """
    __tablename__ = 'alert_history'
    __bind_key__ = 'traffic'  # 指定使用traffic数据库
    
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, nullable=False, index=True)  # 移除外键约束以兼容MySQL权限限制
    alert_type = db.Column(db.String(50), nullable=False, index=True)  # 'traffic_threshold' or 'device_offline'
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False, index=True)  # 'critical', 'warning', 'info'
    
    triggered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='triggered', index=True)  # 'triggered', 'resolved', 'acknowledged'
    
    device_id = db.Column(db.Integer, nullable=True, index=True)  # 移除外键约束以兼容MySQL权限限制
    
    # 创建索引以提高查询性能
    __table_args__ = (
        Index('idx_alert_history_status_triggered', 'status', 'triggered_at'),
    )
    
    def __repr__(self):
        return f'<AlertHistory {self.id} - {self.alert_type} - {self.status}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'alert_type': self.alert_type,
            'message': self.message,
            'severity': self.severity,
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'status': self.status,
            'device_id': self.device_id,
            # 'rule': self.rule.to_dict() if self.rule else None  # 关系定义已移除，需要通过rule_id查询
        }

