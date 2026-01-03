#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份数据模型
存储备份历史记录
"""
from datetime import datetime
import json

# 使用user_models中的db实例
from app.models.user_models import db


class BackupHistory(db.Model):
    """
    备份历史记录表
    存储在users数据库中
    """
    __tablename__ = 'backup_history'
    
    id = db.Column(db.Integer, primary_key=True)
    backup_filename = db.Column(db.String(255), nullable=False)
    backup_path = db.Column(db.String(512), nullable=False)
    backup_size = db.Column(db.BigInteger, nullable=False)  # 文件大小（字节）
    databases = db.Column(db.Text, nullable=False)  # JSON格式的数据库列表
    status = db.Column(db.String(20), nullable=False, default='success')  # success/failed
    error_message = db.Column(db.Text, nullable=True)  # 错误信息
    cloud_uploaded = db.Column(db.Boolean, default=False, nullable=False)  # 是否已上传到云存储
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """转换为字典"""
        try:
            databases_list = json.loads(self.databases) if self.databases else []
        except:
            databases_list = []
        
        return {
            'id': self.id,
            'backup_filename': self.backup_filename,
            'backup_path': self.backup_path,
            'backup_size': self.backup_size,
            'backup_size_formatted': self._format_size(self.backup_size),
            'databases': databases_list,
            'status': self.status,
            'error_message': self.error_message,
            'cloud_uploaded': self.cloud_uploaded,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def _format_size(size_bytes):
        """格式化文件大小"""
        try:
            size_bytes = int(size_bytes)
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.2f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.2f} PB"
        except:
            return "0 B"


def init_backup_db(app):
    """
    初始化备份数据库表
    
    Args:
        app: Flask应用实例
    """
    with app.app_context():
        db.create_all()

