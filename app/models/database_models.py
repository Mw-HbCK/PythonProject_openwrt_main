#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模型定义
存储API请求的历史数据
"""
from datetime import datetime
from sqlalchemy import Index

# 使用user_models中的db实例，避免创建多个SQLAlchemy实例
from app.models.user_models import db


class Device(db.Model):
    """
    设备信息表
    """
    __tablename__ = 'devices'
    __bind_key__ = 'traffic'  # 指定使用traffic数据库
    
    id = db.Column(db.Integer, primary_key=True)
    mac = db.Column(db.String(17), unique=True, nullable=False, index=True)
    hostname = db.Column(db.String(255), nullable=True)
    ip = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系（移除外键约束后，关系定义暂时移除以避免SQLAlchemy配置错误）
    # 应用代码可以通过device_id直接查询
    # traffic_records = db.relationship('DeviceTraffic', backref='device', lazy='dynamic')
    
    def __repr__(self):
        return f'<Device {self.mac} - {self.hostname}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'mac': self.mac,
            'hostname': self.hostname,
            'ip': self.ip,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class TotalTraffic(db.Model):
    """
    全网流量数据表
    """
    __tablename__ = 'total_traffic'
    __bind_key__ = 'traffic'  # 指定使用traffic数据库
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True, default=datetime.utcnow)
    timestamp_ms = db.Column(db.BigInteger, nullable=True, index=True)  # 原始时间戳（毫秒）
    
    # 流量数据（字节）
    down_speed_bytes = db.Column(db.BigInteger, nullable=False)
    up_speed_bytes = db.Column(db.BigInteger, nullable=False)
    total_download_bytes = db.Column(db.BigInteger, nullable=False)
    total_upload_bytes = db.Column(db.BigInteger, nullable=False)
    
    # 格式化后的字符串（用于展示）
    down_speed_formatted = db.Column(db.String(50), nullable=True)
    up_speed_formatted = db.Column(db.String(50), nullable=True)
    total_download_formatted = db.Column(db.String(50), nullable=True)
    total_upload_formatted = db.Column(db.String(50), nullable=True)
    
    # 创建索引以提高查询性能
    __table_args__ = (
        Index('idx_total_traffic_timestamp', 'timestamp'),
    )
    
    def __repr__(self):
        return f'<TotalTraffic {self.timestamp} - Down: {self.down_speed_formatted}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'timestamp_ms': self.timestamp_ms,
            'down_speed': {
                'bytes': self.down_speed_bytes,
                'formatted': self.down_speed_formatted
            },
            'up_speed': {
                'bytes': self.up_speed_bytes,
                'formatted': self.up_speed_formatted
            },
            'total_download': {
                'bytes': self.total_download_bytes,
                'formatted': self.total_download_formatted
            },
            'total_upload': {
                'bytes': self.total_upload_bytes,
                'formatted': self.total_upload_formatted
            }
        }


class DeviceTraffic(db.Model):
    """
    设备流量数据表
    """
    __tablename__ = 'device_traffic'
    __bind_key__ = 'traffic'  # 指定使用traffic数据库
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, nullable=False, index=True)  # 移除外键约束以兼容MySQL权限限制
    timestamp = db.Column(db.DateTime, nullable=False, index=True, default=datetime.utcnow)
    timestamp_ms = db.Column(db.BigInteger, nullable=True, index=True)  # 原始时间戳（毫秒）
    
    # 流量数据（字节）
    down_speed_bytes = db.Column(db.BigInteger, nullable=False)
    up_speed_bytes = db.Column(db.BigInteger, nullable=False)
    total_download_bytes = db.Column(db.BigInteger, nullable=False)
    total_upload_bytes = db.Column(db.BigInteger, nullable=False)
    
    # 格式化后的字符串（用于展示）
    down_speed_formatted = db.Column(db.String(50), nullable=True)
    up_speed_formatted = db.Column(db.String(50), nullable=True)
    total_download_formatted = db.Column(db.String(50), nullable=True)
    total_upload_formatted = db.Column(db.String(50), nullable=True)
    
    # 创建索引以提高查询性能
    __table_args__ = (
        Index('idx_device_traffic_device_timestamp', 'device_id', 'timestamp'),
    )
    
    def __repr__(self):
        return f'<DeviceTraffic Device:{self.device_id} {self.timestamp}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'timestamp_ms': self.timestamp_ms,
            'down_speed': {
                'bytes': self.down_speed_bytes,
                'formatted': self.down_speed_formatted
            },
            'up_speed': {
                'bytes': self.up_speed_bytes,
                'formatted': self.up_speed_formatted
            },
            'total_download': {
                'bytes': self.total_download_bytes,
                'formatted': self.total_download_formatted
            },
            'total_upload': {
                'bytes': self.total_upload_bytes,
                'formatted': self.total_upload_formatted
            }
        }


def init_database_tables(app, bind_key='traffic'):
    """
    初始化数据库表
    
    Args:
        app: Flask应用实例
        bind_key: 数据库绑定键，如果使用BINDS配置
    """
    with app.app_context():
        # 导入告警模型以确保表被创建
        from app.models.alert_models import AlertRule, AlertHistory
        
        # 如果指定了bind_key，使用bind创建表
        if bind_key and 'SQLALCHEMY_BINDS' in app.config:
            db.create_all(bind_key=bind_key)
        else:
            db.create_all()
        print("流量数据库表初始化完成")

