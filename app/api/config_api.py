#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理API路由
"""
from flask import Blueprint, request, jsonify, session
from functools import wraps
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.services.config_manager import load_config_file, save_config_file, validate_config, get_config_file_path
from app.api.user_api import login_required, admin_required
from app.models.user_models import User

config_bp = Blueprint('config', __name__, url_prefix='/api/config')


@config_bp.route('', methods=['GET'])
@login_required
def get_config():
    """
    获取当前配置
    ---
    tags:
      - 系统信息
    summary: 获取系统配置
    description: 获取当前系统配置，密码字段默认隐藏
    security:
      - SessionAuth: []
    produces:
      - application/json
    parameters:
      - in: query
        name: full
        type: boolean
        description: 是否返回完整配置（包括密码），默认false
        default: false
    responses:
      200:
        description: 成功返回配置
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                bandix:
                  type: object
                api:
                  type: object
                collector:
                  type: object
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        config_file = get_config_file_path()
        bandix_config, api_config, collector_config = load_config_file(config_file)
        
        # 检查是否为管理员
        user_id = session.get('user_id')
        is_admin = False
        if user_id:
            user = User.query.get(user_id)
            is_admin = user.is_admin() if user else False
        
        # 管理员可以查看完整配置，普通用户只能查看隐藏敏感信息的配置
        show_full = request.args.get('full', 'false').lower() == 'true' and is_admin
        
        # 处理密码字段
        bandix_config_display = bandix_config.copy()
        if not show_full and 'password' in bandix_config_display:
            bandix_config_display['password'] = '***'
        
        # 处理API密钥字段
        api_config_display = api_config.copy()
        if not show_full and 'api_key' in api_config_display:
            api_config_display['api_key'] = '***'
        
        return jsonify({
            'success': True,
            'data': {
                'bandix': bandix_config_display,
                'api': api_config_display,
                'collector': collector_config
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@config_bp.route('', methods=['PUT'])
@admin_required
def update_config():
    """
    更新配置
    ---
    tags:
      - 系统信息
    summary: 更新系统配置
    description: 更新系统配置，支持部分更新
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
            bandix:
              type: object
              properties:
                url:
                  type: string
                username:
                  type: string
                password:
                  type: string
            api:
              type: object
              properties:
                host:
                  type: string
                port:
                  type: integer
                debug:
                  type: boolean
                auth_enabled:
                  type: boolean
                api_key:
                  type: string
                health_check_require_auth:
                  type: boolean
            collector:
              type: object
              properties:
                collect_interval:
                  type: number
    responses:
      200:
        description: 更新成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
            requires_restart:
              type: boolean
              description: 是否需要重启服务
      400:
        description: 请求参数错误或验证失败
      401:
        description: 未登录
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
        
        config_file = get_config_file_path()
        
        # 读取现有配置
        bandix_config, api_config, collector_config = load_config_file(config_file)
        
        # 更新配置
        if 'bandix' in data:
            bandix_config.update(data['bandix'])
        
        if 'api' in data:
            api_config.update(data['api'])
        
        if 'collector' in data:
            collector_config.update(data['collector'])
        
        # 验证配置
        is_valid, error_msg = validate_config(
            bandix_config if 'bandix' in data else None,
            api_config if 'api' in data else None,
            collector_config if 'collector' in data else None
        )
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # 保存配置
        save_config_file(
            bandix_config if 'bandix' in data else None,
            api_config if 'api' in data else None,
            collector_config if 'collector' in data else None,
            config_file
        )
        
        # 检查是否需要重启服务
        requires_restart = False
        if 'api' in data:
            if 'port' in data['api'] or 'host' in data['api']:
                requires_restart = True
        
        # 重新加载配置到内存
        # 注意：由于循环导入问题，这里通过sys.modules访问已加载的模块
        try:
            bandix_api_module = sys.modules.get('app.bandix_api')
            if bandix_api_module and hasattr(bandix_api_module, 'reload_app_config'):
                bandix_api_module.reload_app_config()
            else:
                # 如果模块未加载，尝试导入
                from app import bandix_api
                if hasattr(bandix_api, 'reload_app_config'):
                    bandix_api.reload_app_config()
        except Exception as e:
            print(f"重新加载配置失败: {e}", file=sys.stderr)
            # 不抛出异常，配置已保存到文件，只是内存中的配置未更新
        
        # 重新加载数据收集服务配置
        try:
            from app.services.data_collector import reload_collector_config
            reload_collector_config()
        except Exception as e:
            print(f"重新加载数据收集服务配置失败: {e}", file=sys.stderr)
        
        message = '配置已更新'
        if requires_restart:
            message += '。注意：修改了端口或主机地址，需要重启服务才能生效'
        
        return jsonify({
            'success': True,
            'message': message,
            'requires_restart': requires_restart
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@config_bp.route('/collector', methods=['GET'])
@login_required
def get_collector_config():
    """
    获取数据收集服务配置
    ---
    tags:
      - 系统信息
    summary: 获取数据收集服务配置
    description: 获取数据收集服务的配置信息
    security:
      - SessionAuth: []
    produces:
      - application/json
    responses:
      200:
        description: 成功返回配置
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                collect_interval:
                  type: number
                is_running:
                  type: boolean
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        config_file = get_config_file_path()
        _, _, collector_config = load_config_file(config_file)
        
        # 获取运行状态
        try:
            from app.services.data_collector import IS_RUNNING, COLLECT_INTERVAL
            is_running = IS_RUNNING
            current_interval = COLLECT_INTERVAL
        except:
            is_running = False
            current_interval = float(collector_config.get('collect_interval', '1.0'))
        
        return jsonify({
            'success': True,
            'data': {
                'collect_interval': current_interval,
                'is_running': is_running
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

