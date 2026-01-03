#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL管理API
提供MySQL连接测试、配置管理、状态检查等API端点
"""
from flask import Blueprint, request, jsonify, session
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.api.user_api import login_required, admin_required
from app.services.database_config_service import (
    get_database_config,
    save_database_config,
    validate_mysql_connection,
    validate_database_config
)

mysql_bp = Blueprint('mysql', __name__, url_prefix='/api/mysql')


@mysql_bp.route('/config', methods=['GET'])
@login_required
@admin_required
def get_mysql_config():
    """
    获取MySQL配置
    ---
    tags:
      - MySQL管理
    summary: 获取MySQL配置
    description: 获取当前MySQL数据库配置（管理员权限）
    security:
      - SessionAuth: []
    responses:
      200:
        description: 成功返回配置
        schema:
          type: object
          properties:
            success:
              type: boolean
            data:
              type: object
      403:
        description: 无权限
      500:
        description: 服务器内部错误
    """
    try:
        config = get_database_config()
        # 不返回密码
        safe_config = config.copy()
        if 'mysql_password' in safe_config:
            safe_config['mysql_password'] = ''  # 密码不返回，前端需要重新输入
        return jsonify({
            'success': True,
            'data': safe_config
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mysql_bp.route('/config', methods=['POST'])
@login_required
@admin_required
def save_mysql_config():
    """
    保存MySQL配置
    ---
    tags:
      - MySQL管理
    summary: 保存MySQL配置
    description: 保存MySQL数据库配置（管理员权限）
    security:
      - SessionAuth: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            mysql_host:
              type: string
            mysql_port:
              type: string
            mysql_user:
              type: string
            mysql_password:
              type: string
            mysql_database:
              type: string
            mysql_charset:
              type: string
    responses:
      200:
        description: 保存成功
      400:
        description: 请求参数错误或验证失败
      403:
        description: 无权限
      500:
        description: 服务器内部错误
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400
        
        # 验证配置
        is_valid, error_msg = validate_database_config(data)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # 如果密码为空，从现有配置中获取
        if not data.get('mysql_password'):
            existing_config = get_database_config()
            if 'mysql_password' in existing_config:
                data['mysql_password'] = existing_config['mysql_password']
        
        # 验证MySQL连接
        is_valid, error_msg = validate_mysql_connection(data)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # 保存配置
        save_database_config(data)
        
        return jsonify({
            'success': True,
            'message': 'MySQL配置已保存'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mysql_bp.route('/test-connection', methods=['POST'])
@login_required
@admin_required
def test_mysql_connection():
    """
    测试MySQL连接
    ---
    tags:
      - MySQL管理
    summary: 测试MySQL连接
    description: 测试MySQL数据库连接（管理员权限）
    security:
      - SessionAuth: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            mysql_host:
              type: string
            mysql_port:
              type: string
            mysql_user:
              type: string
            mysql_password:
              type: string
            mysql_database:
              type: string
            mysql_charset:
              type: string
    responses:
      200:
        description: 连接测试结果
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
      400:
        description: 请求参数错误
      403:
        description: 无权限
      500:
        description: 服务器内部错误
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400
        
        # 如果密码为空，从现有配置中获取
        if not data.get('mysql_password'):
            existing_config = get_database_config()
            if 'mysql_password' in existing_config:
                data['mysql_password'] = existing_config['mysql_password']
        
        # 验证MySQL连接
        is_valid, error_msg = validate_mysql_connection(data)
        if is_valid:
            return jsonify({
                'success': True,
                'message': 'MySQL连接成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mysql_bp.route('/status', methods=['GET'])
@login_required
@admin_required
def get_mysql_status():
    """
    获取MySQL连接状态和数据库信息
    ---
    tags:
      - MySQL管理
    summary: 获取MySQL状态
    description: 获取MySQL数据库连接状态和数据库信息（管理员权限）
    security:
      - SessionAuth: []
    responses:
      200:
        description: 成功返回状态
        schema:
          type: object
          properties:
            success:
              type: boolean
            data:
              type: object
              properties:
                connected:
                  type: boolean
                host:
                  type: string
                port:
                  type: string
                database:
                  type: string
                message:
                  type: string
      403:
        description: 无权限
      500:
        description: 服务器内部错误
    """
    try:
        config = get_database_config()
        
        # 验证连接
        is_valid, error_msg = validate_mysql_connection(config)
        
        status_data = {
            'connected': is_valid,
            'host': config.get('mysql_host', ''),
            'port': config.get('mysql_port', '3306'),
            'database': config.get('mysql_database', ''),
            'message': '连接成功' if is_valid else (error_msg or '连接失败')
        }
        
        return jsonify({
            'success': True,
            'data': status_data
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

