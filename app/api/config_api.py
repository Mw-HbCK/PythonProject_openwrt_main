#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理API路由
"""
from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime
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
        bandix_config, api_config, collector_config, notifications_config, backup_config, report_config, logging_config, database_config = load_config_file(config_file)
        
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
        
        # 处理通知配置中的敏感字段
        notifications_config_display = notifications_config.copy()
        if not show_full:
            if 'email_password' in notifications_config_display:
                notifications_config_display['email_password'] = '***'
            if 'telegram_bot_token' in notifications_config_display:
                notifications_config_display['telegram_bot_token'] = '***'
            # Webhook URL 包含敏感信息，但通常不需要完全隐藏，只隐藏部分即可
            # 如果需要，可以在这里添加处理逻辑
        
        # 处理备份配置中的敏感字段
        backup_config_display = backup_config.copy()
        if not show_full:
            if 'cloud_access_key' in backup_config_display:
                backup_config_display['cloud_access_key'] = '***'
            if 'cloud_secret_key' in backup_config_display:
                backup_config_display['cloud_secret_key'] = '***'
        
        return jsonify({
            'success': True,
            'data': {
                'bandix': bandix_config_display,
                'api': api_config_display,
                'collector': collector_config,
                'notifications': notifications_config_display,
                'backup': backup_config_display,
                'report': report_config,
                'logging': logging_config
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
        bandix_config, api_config, collector_config, notifications_config, backup_config, report_config, logging_config, database_config = load_config_file(config_file)
        
        # 更新配置
        if 'bandix' in data:
            bandix_config.update(data['bandix'])
        
        if 'api' in data:
            api_config.update(data['api'])
        
        if 'collector' in data:
            collector_config.update(data['collector'])
        
        if 'notifications' in data:
            notifications_config.update(data['notifications'])
        
        if 'backup' in data:
            backup_config.update(data['backup'])
        
        if 'report' in data:
            report_config.update(data['report'])
        
        if 'logging' in data:
            logging_config.update(data['logging'])
        
        # 验证配置
        is_valid, error_msg = validate_config(
            bandix_config if 'bandix' in data else None,
            api_config if 'api' in data else None,
            collector_config if 'collector' in data else None,
            notifications_config if 'notifications' in data else None,
            backup_config if 'backup' in data else None,
            report_config if 'report' in data else None,
            logging_config if 'logging' in data else None
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
            notifications_config if 'notifications' in data else None,
            backup_config if 'backup' in data else None,
            report_config if 'report' in data else None,
            logging_config if 'logging' in data else None,
            None,  # database_config
            config_file
        )
        
        # 如果更新了日志配置，重新初始化日志系统
        if 'logging' in data:
            try:
                from app.services.logger_service import init_logging
                init_logging(logging_config)
            except Exception as e:
                print(f"重新初始化日志系统失败: {e}", file=sys.stderr)
        
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


@config_bp.route('/notifications', methods=['GET'])
@login_required
def get_notifications_config():
    """
    获取通知配置
    ---
    tags:
      - 系统信息
    summary: 获取通知配置
    description: 获取通知渠道的配置信息
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
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        config_file = get_config_file_path()
        _, _, _, notifications_config, _, _, _, _ = load_config_file(config_file)
        
        # 检查是否为管理员
        user_id = session.get('user_id')
        is_admin = False
        if user_id:
            user = User.query.get(user_id)
            is_admin = user.is_admin() if user else False
        
        # 管理员可以查看完整配置，普通用户只能查看隐藏敏感信息的配置
        show_full = request.args.get('full', 'false').lower() == 'true' and is_admin
        
        # 处理敏感字段
        notifications_config_display = notifications_config.copy()
        if not show_full:
            if 'email_password' in notifications_config_display:
                notifications_config_display['email_password'] = '***'
            if 'telegram_bot_token' in notifications_config_display:
                notifications_config_display['telegram_bot_token'] = '***'
        
        return jsonify({
            'success': True,
            'data': notifications_config_display
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@config_bp.route('/notifications', methods=['PUT'])
@admin_required
def update_notifications_config():
    """
    更新通知配置
    ---
    tags:
      - 系统信息
    summary: 更新通知配置
    description: 更新通知渠道的配置
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
            email_enabled:
              type: boolean
            email_smtp_host:
              type: string
            email_smtp_port:
              type: integer
            email_use_tls:
              type: boolean
            email_username:
              type: string
            email_password:
              type: string
            email_from:
              type: string
            email_to:
              type: string
            webhook_enabled:
              type: boolean
            webhook_urls:
              type: string
            webhook_headers:
              type: string
            telegram_enabled:
              type: boolean
            telegram_bot_token:
              type: string
            telegram_chat_ids:
              type: string
    responses:
      200:
        description: 更新成功
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
        bandix_config, api_config, collector_config, notifications_config, backup_config, report_config, _, _ = load_config_file(config_file)
        
        # 更新通知配置
        notifications_config.update(data)
        
        # 验证配置
        is_valid, error_msg = validate_config(
            None, None, None, notifications_config, None
        )
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # 保存配置
        save_config_file(
            None, None, None, notifications_config, None, None, config_file
        )
        
        # 重新加载通知服务配置
        try:
            from app.services.notification_service import NotificationService
            # 通知服务会在下次使用时重新加载配置，这里不需要手动重新加载
        except Exception as e:
            print(f"重新加载通知服务配置失败: {e}", file=sys.stderr)
        
        return jsonify({
            'success': True,
            'message': '通知配置已更新'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@config_bp.route('/notifications/test', methods=['POST'])
@admin_required
def test_notifications():
    """
    测试通知配置
    ---
    tags:
      - 系统信息
    summary: 测试通知配置
    description: 发送测试通知到指定的通知渠道
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
            channels:
              type: array
              items:
                type: string
              description: 要测试的通知渠道列表，如 ['email', 'webhook', 'telegram']
              example: ['email']
    responses:
      200:
        description: 测试完成
      400:
        description: 请求参数错误
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
        
        channels = data.get('channels', [])
        if not isinstance(channels, list) or len(channels) == 0:
            return jsonify({
                'success': False,
                'error': 'channels 必须是非空数组'
            }), 400
        
        # 创建测试告警记录
        test_alert_history = {
            'alert_type': 'test',
            'message': '这是一条测试告警消息。如果您收到此消息，说明通知配置正确。',
            'severity': 'info',
            'triggered_at': datetime.utcnow().isoformat()
        }
        
        # 发送测试通知
        from app.services.notification_service import NotificationService
        notification_service = NotificationService()
        results = notification_service.send_notification(channels, test_alert_history)
        
        # 汇总结果
        success_count = sum(1 for success, _ in results.values() if success)
        total_count = len(results)
        
        return jsonify({
            'success': True,
            'message': f'测试完成: {success_count}/{total_count} 成功',
            'data': {
                'total_channels': total_count,
                'success_count': success_count,
                'results': {
                    channel: {
                        'success': success,
                        'message': msg
                    }
                    for channel, (success, msg) in results.items()
                }
            }
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
        _, _, collector_config, _, _, _, _, _ = load_config_file(config_file)
        
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

