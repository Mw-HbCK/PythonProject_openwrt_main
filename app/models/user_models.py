#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户数据模型
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import secrets
import hashlib

db = SQLAlchemy()


class User(db.Model):
    """
    用户模型
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(20), default='user', nullable=False)  # 'admin' or 'user'
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @staticmethod
    def hash_password(password):
        """
        密码哈希
        """
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    @staticmethod
    def generate_token():
        """
        生成唯一token
        """
        return secrets.token_urlsafe(48)
    
    def check_password(self, password):
        """
        验证密码
        """
        return self.password_hash == User.hash_password(password)
    
    def is_admin(self):
        """
        检查用户是否为管理员
        """
        return self.role == 'admin'
    
    def to_dict(self):
        """
        转换为字典
        """
        return {
            'id': self.id,
            'username': self.username,
            'token': self.token,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
            'role': self.role
        }


def migrate_db(app):
    """
    数据库迁移：为现有用户添加role字段
    """
    with app.app_context():
        try:
            # 检查role列是否存在
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            if 'role' not in columns:
                # SQLite 3.25.0+支持ALTER TABLE ADD COLUMN
                print("检测到需要添加role字段，执行数据库迁移...")
                
                try:
                    # 使用SQLAlchemy的text()和session.execute()
                    db.session.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'"))
                    db.session.commit()
                    print("成功添加role字段")
                except Exception as e:
                    print(f"使用ALTER TABLE添加字段失败: {e}")
                    db.session.rollback()
                    # 如果ALTER TABLE失败，SQLite版本可能较低
                    # 但我们仍然可以尝试为现有记录设置默认值
                    print("继续为现有用户设置默认角色...")
                
                # 为现有用户设置默认role
                users = User.query.all()
                for user in users:
                    # 使用getattr安全获取role属性，如果不存在则为None
                    user_role = getattr(user, 'role', None)
                    if user_role is None:
                        # 如果username是admin，设置为admin角色，否则为user
                        if user.username == 'admin':
                            user.role = 'admin'
                        else:
                            user.role = 'user'
                
                # 确保admin用户是管理员
                admin = User.query.filter_by(username='admin').first()
                if admin:
                    admin.role = 'admin'
                
                db.session.commit()
                print("数据库迁移完成")
        except Exception as e:
            print(f"数据库迁移过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()


def init_db(app):
    """
    初始化数据库
    """
    with app.app_context():
        db.create_all()
        
        # 执行数据库迁移（如果需要）
        migrate_db(app)
        
        # 检查是否已有管理员用户
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # 创建默认管理员用户（密码：admin123）
            admin = User(
                username='admin',
                password_hash=User.hash_password('admin123'),
                token=User.generate_token(),
                is_active=True,
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print(f"创建默认管理员用户: admin / admin123")
            print(f"管理员 Token: {admin.token}")
        else:
            # 确保现有admin用户是管理员角色
            if admin.role != 'admin':
                admin.role = 'admin'
                db.session.commit()
                print("已将admin用户设置为管理员角色")

