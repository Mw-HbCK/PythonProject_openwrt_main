#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报表数据模型
存储报表历史记录
"""
from datetime import datetime
import json

# 使用user_models中的db实例
from app.models.user_models import db


class ReportHistory(db.Model):
    """
    报表历史记录表
    存储在users数据库中
    """
    __tablename__ = 'report_history'
    
    id = db.Column(db.Integer, primary_key=True)
    report_type = db.Column(db.String(20), nullable=False, index=True)  # daily/weekly/monthly
    report_period = db.Column(db.String(20), nullable=False)  # 报表周期（如2026-01-01表示当天的日报）
    file_path_pdf = db.Column(db.String(512), nullable=True)  # PDF文件路径
    file_path_html = db.Column(db.String(512), nullable=True)  # HTML文件路径（可选）
    file_path_excel = db.Column(db.String(512), nullable=True)  # Excel文件路径（可选）
    file_size = db.Column(db.BigInteger, nullable=False, default=0)  # 文件大小（字节）
    status = db.Column(db.String(20), nullable=False, default='success')  # success/failed
    error_message = db.Column(db.Text, nullable=True)  # 错误信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    sent_at = db.Column(db.DateTime, nullable=True)  # 邮件发送时间（如果已发送）
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'report_type': self.report_type,
            'report_period': self.report_period,
            'file_path_pdf': self.file_path_pdf,
            'file_path_html': self.file_path_html,
            'file_path_excel': self.file_path_excel,
            'file_size': self.file_size,
            'file_size_formatted': self._format_size(self.file_size),
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None
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


def init_report_db(app):
    """
    初始化报表数据库表
    
    Args:
        app: Flask应用实例
    """
    with app.app_context():
        db.create_all()

