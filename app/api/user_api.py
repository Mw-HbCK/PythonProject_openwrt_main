#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户管理API路由
"""
from flask import Blueprint, request, jsonify, session, render_template_string
from functools import wraps
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.models.user_models import db, User

user_bp = Blueprint('user', __name__, url_prefix='/api/user')


def login_required(f):
    """
    登录验证装饰器
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'message': '请先登录'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    管理员权限验证装饰器
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'message': '请先登录'
            }), 401
        
        # 获取用户信息并检查是否为管理员
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if not user:
            session.clear()
            return jsonify({
                'success': False,
                'message': '用户不存在'
            }), 404
        
        if not user.is_admin():
            return jsonify({
                'success': False,
                'message': '需要管理员权限'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function


@user_bp.route('/register', methods=['POST'])
def register():
    """
    用户注册
    ---
    tags:
      - 用户管理
    summary: 用户注册
    description: 注册新用户账户，注册成功后返回用户名和Token
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        description: 注册信息
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              description: 用户名（至少3个字符）
              example: "testuser"
            password:
              type: string
              description: 密码（至少6个字符）
              example: "password123"
    responses:
      201:
        description: 注册成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "注册成功"
            data:
              type: object
              properties:
                username:
                  type: string
                  example: "testuser"
                token:
                  type: string
                  example: "abc123def456..."
      400:
        description: 请求参数错误或用户名已存在
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "用户名已存在"
      500:
        description: 服务器内部错误
    """
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        # 验证输入
        if not username or not password:
            return jsonify({
                'success': False,
                'message': '用户名和密码不能为空'
            }), 400
        
        if len(username) < 3:
            return jsonify({
                'success': False,
                'message': '用户名至少需要3个字符'
            }), 400
        
        if len(password) < 6:
            return jsonify({
                'success': False,
                'message': '密码至少需要6个字符'
            }), 400
        
        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            return jsonify({
                'success': False,
                'message': '用户名已存在'
            }), 400
        
        # 创建新用户
        user = User(
            username=username,
            password_hash=User.hash_password(password),
            token=User.generate_token(),
            is_active=True
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '注册成功',
            'data': {
                'username': user.username,
                'token': user.token
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'注册失败: {str(e)}'
        }), 500


@user_bp.route('/login', methods=['POST'])
def login():
    """
    用户登录
    ---
    tags:
      - 用户管理
    summary: 用户登录
    description: 用户登录，登录成功后设置Session并返回Token
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        description: 登录信息
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              description: 用户名
              example: "testuser"
            password:
              type: string
              description: 密码
              example: "password123"
    responses:
      200:
        description: 登录成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "登录成功"
            data:
              type: object
              properties:
                username:
                  type: string
                  example: "testuser"
                token:
                  type: string
                  example: "abc123def456..."
      400:
        description: 请求参数错误
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "用户名和密码不能为空"
      401:
        description: 用户名或密码错误
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "用户名或密码错误"
      403:
        description: 账户已被禁用
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "账户已被禁用"
      500:
        description: 服务器内部错误
    """
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({
                'success': False,
                'message': '用户名和密码不能为空'
            }), 400
        
        # 查找用户
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            return jsonify({
                'success': False,
                'message': '用户名或密码错误'
            }), 401
        
        if not user.is_active:
            return jsonify({
                'success': False,
                'message': '账户已被禁用'
            }), 403
        
        # 设置session
        session['user_id'] = user.id
        session['username'] = user.username
        session['user_role'] = user.role  # 存储用户角色
        
        return jsonify({
            'success': True,
            'message': '登录成功',
            'data': {
                'username': user.username,
                'token': user.token,
                'role': user.role
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'登录失败: {str(e)}'
        }), 500


@user_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """
    用户登出
    ---
    tags:
      - 用户管理
    summary: 用户登出
    description: 用户登出，清除Session
    security:
      - SessionAuth: []
    produces:
      - application/json
    responses:
      200:
        description: 登出成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "登出成功"
      401:
        description: 未登录
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "请先登录"
    """
    session.clear()
    return jsonify({
        'success': True,
        'message': '登出成功'
    })


@user_bp.route('/info', methods=['GET'])
@login_required
def get_user_info():
    """
    获取当前用户信息
    ---
    tags:
      - 用户管理
    summary: 获取当前用户信息
    description: 获取当前登录用户的详细信息，包括用户名、Token等
    security:
      - SessionAuth: []
    produces:
      - application/json
    responses:
      200:
        description: 获取成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                id:
                  type: integer
                  example: 1
                username:
                  type: string
                  example: "testuser"
                token:
                  type: string
                  example: "abc123def456..."
                is_active:
                  type: boolean
                  example: true
                created_at:
                  type: string
                  format: date-time
                  example: "2023-12-21T10:30:00"
      401:
        description: 未登录
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "请先登录"
      404:
        description: 用户不存在
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "用户不存在"
      500:
        description: 服务器内部错误
    """
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if not user:
            session.clear()
            return jsonify({
                'success': False,
                'message': '用户不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'data': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取用户信息失败: {str(e)}'
        }), 500


@user_bp.route('/token/refresh', methods=['POST'])
@login_required
def refresh_token():
    """
    刷新用户Token
    ---
    tags:
      - 用户管理
    summary: 刷新用户Token
    description: 为当前登录用户生成新的Token，旧Token将失效
    security:
      - SessionAuth: []
    produces:
      - application/json
    responses:
      200:
        description: Token刷新成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Token刷新成功"
            data:
              type: object
              properties:
                token:
                  type: string
                  example: "new_abc123def456..."
      401:
        description: 未登录
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "请先登录"
      404:
        description: 用户不存在
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "用户不存在"
      500:
        description: 服务器内部错误
    """
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if not user:
            session.clear()
            return jsonify({
                'success': False,
                'message': '用户不存在'
            }), 404
        
        # 生成新token
        user.token = User.generate_token()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Token刷新成功',
            'data': {
                'token': user.token
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'刷新Token失败: {str(e)}'
        }), 500


@user_bp.route('/list', methods=['GET'])
@admin_required
def list_users():
    """
    获取用户列表
    ---
    tags:
      - 用户管理
    summary: 获取用户列表
    description: 获取所有用户列表，支持分页（仅管理员）
    security:
      - SessionAuth: []
    produces:
      - application/json
    parameters:
      - in: query
        name: page
        type: integer
        description: 页码（从1开始）
        default: 1
      - in: query
        name: per_page
        type: integer
        description: 每页数量
        default: 20
    responses:
      200:
        description: 成功返回用户列表
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                users:
                  type: array
                  items:
                    type: object
                total:
                  type: integer
                  example: 10
                page:
                  type: integer
                  example: 1
                per_page:
                  type: integer
                  example: 20
      401:
        description: 未登录
      403:
        description: 需要管理员权限
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = min(per_page, 100)  # 限制每页最多100条
        
        pagination = User.query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        users = [user.to_dict() for user in pagination.items]
        
        return jsonify({
            'success': True,
            'data': {
                'users': users,
                'total': pagination.total,
                'page': pagination.page,
                'per_page': pagination.per_page,
                'pages': pagination.pages
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取用户列表失败: {str(e)}'
        }), 500


@user_bp.route('/<int:user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    """
    获取用户详情
    ---
    tags:
      - 用户管理
    summary: 获取用户详情
    description: 获取指定用户的详细信息（仅管理员）
    security:
      - SessionAuth: []
    produces:
      - application/json
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: 用户ID
    responses:
      200:
        description: 成功返回用户信息
      401:
        description: 未登录
      403:
        description: 需要管理员权限
      404:
        description: 用户不存在
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': '用户不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'data': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取用户信息失败: {str(e)}'
        }), 500


@user_bp.route('/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """
    更新用户信息
    ---
    tags:
      - 用户管理
    summary: 更新用户信息
    description: 更新用户信息（角色、状态等），仅管理员，不能修改自己的角色（仅管理员）
    security:
      - SessionAuth: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: 用户ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            role:
              type: string
              enum: [admin, user]
            is_active:
              type: boolean
    responses:
      200:
        description: 更新成功
      400:
        description: 请求参数错误
      401:
        description: 未登录
      403:
        description: 需要管理员权限或不能修改自己的角色
      404:
        description: 用户不存在
    """
    try:
        current_user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': '用户不存在'
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求体不能为空'
            }), 400
        
        # 不能修改自己的角色
        if user_id == current_user_id and 'role' in data:
            return jsonify({
                'success': False,
                'message': '不能修改自己的角色'
            }), 403
        
        # 更新用户信息
        if 'role' in data:
            role = data['role'].strip().lower()
            if role not in ['admin', 'user']:
                return jsonify({
                    'success': False,
                    'message': '角色必须是admin或user'
                }), 400
            user.role = role
        
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '用户信息更新成功',
            'data': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'更新用户信息失败: {str(e)}'
        }), 500


@user_bp.route('/<int:user_id>/toggle', methods=['POST'])
@admin_required
def toggle_user(user_id):
    """
    启用/禁用用户
    ---
    tags:
      - 用户管理
    summary: 启用/禁用用户
    description: 启用或禁用用户账户，仅管理员，不能禁用自己（仅管理员）
    security:
      - SessionAuth: []
    produces:
      - application/json
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: 用户ID
    responses:
      200:
        description: 操作成功
      401:
        description: 未登录
      403:
        description: 需要管理员权限或不能禁用自己
      404:
        description: 用户不存在
    """
    try:
        current_user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': '用户不存在'
            }), 404
        
        # 不能禁用自己
        if user_id == current_user_id:
            return jsonify({
                'success': False,
                'message': '不能禁用自己的账户'
            }), 403
        
        # 切换状态
        user.is_active = not user.is_active
        db.session.commit()
        
        status_text = '启用' if user.is_active else '禁用'
        
        return jsonify({
            'success': True,
            'message': f'用户已{status_text}',
            'data': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'操作失败: {str(e)}'
        }), 500


@user_bp.route('/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """
    删除用户
    ---
    tags:
      - 用户管理
    summary: 删除用户
    description: 删除用户账户，仅管理员，不能删除自己（仅管理员）
    security:
      - SessionAuth: []
    produces:
      - application/json
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: 用户ID
    responses:
      200:
        description: 删除成功
      401:
        description: 未登录
      403:
        description: 需要管理员权限或不能删除自己
      404:
        description: 用户不存在
    """
    try:
        current_user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': '用户不存在'
            }), 404
        
        # 不能删除自己
        if user_id == current_user_id:
            return jsonify({
                'success': False,
                'message': '不能删除自己的账户'
            }), 403
        
        # 删除用户
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '用户已删除'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'删除用户失败: {str(e)}'
        }), 500

