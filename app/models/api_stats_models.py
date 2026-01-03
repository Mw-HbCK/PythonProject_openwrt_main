#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API调用统计数据模型
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import Index

# 使用用户数据库的db实例
from app.models.user_models import db


class ApiCallStat(db.Model):
    """
    API调用统计模型
    """
    __tablename__ = 'api_call_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.String(255), nullable=False, index=True)
    method = db.Column(db.String(10), nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=True, index=True)  # 移除外键约束以兼容MySQL权限限制
    username = db.Column(db.String(80), nullable=True, index=True)
    status_code = db.Column(db.Integer, nullable=False, default=200)
    call_count = db.Column(db.Integer, default=1, nullable=False)
    last_called_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 创建复合索引以提高查询性能
    __table_args__ = (
        Index('idx_endpoint_method', 'endpoint', 'method'),
        Index('idx_user_endpoint', 'user_id', 'endpoint'),
        Index('idx_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f'<ApiCallStat {self.method} {self.endpoint} - {self.call_count} calls>'
    
    def to_dict(self):
        """
        转换为字典
        """
        return {
            'id': self.id,
            'endpoint': self.endpoint,
            'method': self.method,
            'user_id': self.user_id,
            'username': self.username,
            'status_code': self.status_code,
            'call_count': self.call_count,
            'last_called_at': self.last_called_at.isoformat() if self.last_called_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


def init_api_stats_db(app):
    """
    初始化API统计数据库表
    """
    with app.app_context():
        try:
            db.create_all()
            print("[API统计] 数据库表初始化完成")
        except Exception as e:
            print(f"[API统计] 数据库表初始化失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

