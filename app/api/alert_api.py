#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
告警管理API路由
"""
from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import desc, and_, or_
import os
import sys
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.models.user_models import db, User
from app.models.alert_models import AlertRule, AlertHistory
from app.models.database_models import Device


alert_bp = Blueprint('alert', __name__, url_prefix='/api/alerts')


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


@alert_bp.route('/rules', methods=['GET'])
@login_required
def get_rules():
    """
    获取所有告警规则
    ---
    tags:
      - 告警管理
    summary: 获取所有告警规则
    description: 获取所有告警规则的列表
    security:
      - SessionAuth: []
    produces:
      - application/json
    responses:
      200:
        description: 成功返回告警规则列表
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  name:
                    type: string
                  type:
                    type: string
                    enum: [traffic_threshold, device_offline]
                  enabled:
                    type: boolean
                  threshold_bytes:
                    type: integer
                  device_id:
                    type: integer
                    nullable: true
                  offline_threshold_minutes:
                    type: integer
                    nullable: true
                  severity:
                    type: string
                    enum: [critical, warning, info]
            count:
              type: integer
              example: 5
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        rules = AlertRule.query.order_by(AlertRule.created_at.desc()).all()
        return jsonify({
            'success': True,
            'data': [rule.to_dict() for rule in rules],
            'count': len(rules)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alert_bp.route('/rules/<int:rule_id>', methods=['GET'])
@login_required
def get_rule(rule_id):
    """
    获取单个告警规则
    ---
    tags:
      - 告警管理
    summary: 获取单个告警规则
    description: 根据ID获取单个告警规则的详细信息
    security:
      - SessionAuth: []
    produces:
      - application/json
    parameters:
      - in: path
        name: rule_id
        type: integer
        required: true
        description: 告警规则ID
    responses:
      200:
        description: 成功返回告警规则
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
                name:
                  type: string
                type:
                  type: string
                enabled:
                  type: boolean
      404:
        description: 告警规则不存在
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        rule = AlertRule.query.get(rule_id)
        if not rule:
            return jsonify({
                'success': False,
                'error': '告警规则不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'data': rule.to_dict()
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alert_bp.route('/rules', methods=['POST'])
@login_required
def create_rule():
    """
    创建告警规则
    ---
    tags:
      - 告警管理
    summary: 创建告警规则
    description: 创建一个新的告警规则
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
          required:
            - name
            - type
          properties:
            name:
              type: string
              description: 规则名称
              example: "流量阈值告警"
            type:
              type: string
              enum: [traffic_threshold, device_offline]
              description: 告警类型
              example: "traffic_threshold"
            enabled:
              type: boolean
              description: 是否启用
              example: true
            threshold_bytes:
              type: integer
              description: 流量阈值（字节），type为traffic_threshold时必填
              example: 1073741824
            device_id:
              type: integer
              description: 设备ID，可选，NULL表示所有设备
              example: 1
            offline_threshold_minutes:
              type: integer
              description: 离线阈值（分钟），type为device_offline时必填
              example: 30
            notification_methods:
              type: array
              items:
                type: string
              description: 通知方式列表
              example: ["page"]
            severity:
              type: string
              enum: [critical, warning, info]
              description: 严重程度
              example: "warning"
    responses:
      201:
        description: 创建成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
      400:
        description: 请求参数错误
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('name'):
            return jsonify({
                'success': False,
                'error': '规则名称不能为空'
            }), 400
        
        if not data.get('type') or data.get('type') not in ['traffic_threshold', 'device_offline']:
            return jsonify({
                'success': False,
                'error': '告警类型无效，必须是 traffic_threshold 或 device_offline'
            }), 400
        
        alert_type = data.get('type')
        
        # 根据类型验证字段
        if alert_type == 'traffic_threshold':
            if not data.get('threshold_bytes') or data.get('threshold_bytes') <= 0:
                return jsonify({
                    'success': False,
                    'error': '流量阈值必须大于0'
                }), 400
        elif alert_type == 'device_offline':
            if not data.get('offline_threshold_minutes') or data.get('offline_threshold_minutes') <= 0:
                return jsonify({
                    'success': False,
                    'error': '离线阈值（分钟）必须大于0'
                }), 400
        
        # 处理通知方式
        notification_methods = data.get('notification_methods', ['page'])
        if not isinstance(notification_methods, list):
            notification_methods = ['page']
        
        # 创建规则
        rule = AlertRule(
            name=data.get('name'),
            type=alert_type,
            enabled=data.get('enabled', True),
            threshold_bytes=data.get('threshold_bytes'),
            device_id=data.get('device_id'),
            offline_threshold_minutes=data.get('offline_threshold_minutes'),
            notification_methods=json.dumps(notification_methods),
            severity=data.get('severity', 'warning')
        )
        
        db.session.add(rule)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': rule.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alert_bp.route('/rules/<int:rule_id>', methods=['PUT'])
@login_required
def update_rule(rule_id):
    """
    更新告警规则
    ---
    tags:
      - 告警管理
    summary: 更新告警规则
    description: 更新指定ID的告警规则
    security:
      - SessionAuth: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: path
        name: rule_id
        type: integer
        required: true
        description: 告警规则ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
            type:
              type: string
              enum: [traffic_threshold, device_offline]
            enabled:
              type: boolean
            threshold_bytes:
              type: integer
            device_id:
              type: integer
            offline_threshold_minutes:
              type: integer
            notification_methods:
              type: array
              items:
                type: string
            severity:
              type: string
              enum: [critical, warning, info]
    responses:
      200:
        description: 更新成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
      400:
        description: 请求参数错误
      404:
        description: 告警规则不存在
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        rule = AlertRule.query.get(rule_id)
        if not rule:
            return jsonify({
                'success': False,
                'error': '告警规则不存在'
            }), 404
        
        data = request.get_json()
        
        # 更新字段
        if 'name' in data:
            rule.name = data['name']
        
        if 'enabled' in data:
            rule.enabled = data['enabled']
        
        if 'type' in data:
            if data['type'] not in ['traffic_threshold', 'device_offline']:
                return jsonify({
                    'success': False,
                    'error': '告警类型无效'
                }), 400
            rule.type = data['type']
        
        if 'threshold_bytes' in data:
            rule.threshold_bytes = data['threshold_bytes']
        
        if 'device_id' in data:
            rule.device_id = data['device_id']
        
        if 'offline_threshold_minutes' in data:
            rule.offline_threshold_minutes = data['offline_threshold_minutes']
        
        if 'notification_methods' in data:
            notification_methods = data['notification_methods']
            if isinstance(notification_methods, list):
                rule.notification_methods = json.dumps(notification_methods)
        
        if 'severity' in data:
            if data['severity'] not in ['critical', 'warning', 'info']:
                return jsonify({
                    'success': False,
                    'error': '严重程度无效，必须是 critical、warning 或 info'
                }), 400
            rule.severity = data['severity']
        
        rule.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': rule.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alert_bp.route('/rules/<int:rule_id>', methods=['DELETE'])
@login_required
def delete_rule(rule_id):
    """
    删除告警规则
    ---
    tags:
      - 告警管理
    summary: 删除告警规则
    description: 删除指定ID的告警规则
    security:
      - SessionAuth: []
    produces:
      - application/json
    parameters:
      - in: path
        name: rule_id
        type: integer
        required: true
        description: 告警规则ID
    responses:
      200:
        description: 删除成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "告警规则已删除"
      404:
        description: 告警规则不存在
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        rule = AlertRule.query.get(rule_id)
        if not rule:
            return jsonify({
                'success': False,
                'error': '告警规则不存在'
            }), 404
        
        db.session.delete(rule)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '告警规则已删除'
        })
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alert_bp.route('/history', methods=['GET'])
@login_required
def get_history():
    """
    获取告警历史
    ---
    tags:
      - 告警管理
    summary: 获取告警历史
    description: 获取告警历史记录，支持分页和多种筛选条件
    security:
      - SessionAuth: []
    produces:
      - application/json
    parameters:
      - in: query
        name: page
        type: integer
        description: 页码（默认1）
        default: 1
      - in: query
        name: per_page
        type: integer
        description: 每页数量（默认20）
        default: 20
      - in: query
        name: status
        type: string
        enum: [triggered, resolved, acknowledged]
        description: 状态筛选
      - in: query
        name: alert_type
        type: string
        description: 告警类型筛选
      - in: query
        name: severity
        type: string
        enum: [critical, warning, info]
        description: 严重程度筛选
      - in: query
        name: start_time
        type: string
        format: date-time
        description: 开始时间（ISO格式）
      - in: query
        name: end_time
        type: string
        format: date-time
        description: 结束时间（ISO格式）
    responses:
      200:
        description: 成功返回告警历史
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: array
              items:
                type: object
            pagination:
              type: object
              properties:
                page:
                  type: integer
                per_page:
                  type: integer
                total:
                  type: integer
                pages:
                  type: integer
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 构建查询
        query = AlertHistory.query
        
        # 状态筛选
        status = request.args.get('status')
        if status:
            query = query.filter(AlertHistory.status == status)
        
        # 告警类型筛选
        alert_type = request.args.get('alert_type')
        if alert_type:
            query = query.filter(AlertHistory.alert_type == alert_type)
        
        # 严重程度筛选
        severity = request.args.get('severity')
        if severity:
            query = query.filter(AlertHistory.severity == severity)
        
        # 时间范围筛选
        start_time = request.args.get('start_time')
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                query = query.filter(AlertHistory.triggered_at >= start_dt)
            except ValueError:
                pass
        
        end_time = request.args.get('end_time')
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                query = query.filter(AlertHistory.triggered_at <= end_dt)
            except ValueError:
                pass
        
        # 排序和分页
        query = query.order_by(desc(AlertHistory.triggered_at))
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'data': [history.to_dict() for history in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alert_bp.route('/history/<int:history_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge_alert(history_id):
    """
    确认告警
    ---
    tags:
      - 告警管理
    summary: 确认告警
    description: 将指定告警的状态设置为已确认（acknowledged）
    security:
      - SessionAuth: []
    produces:
      - application/json
    parameters:
      - in: path
        name: history_id
        type: integer
        required: true
        description: 告警历史ID
    responses:
      200:
        description: 确认成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
      404:
        description: 告警记录不存在
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        alert = AlertHistory.query.get(history_id)
        if not alert:
            return jsonify({
                'success': False,
                'error': '告警记录不存在'
            }), 404
        
        alert.status = 'acknowledged'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': alert.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alert_bp.route('/active', methods=['GET'])
@login_required
def get_active_alerts():
    """
    获取活跃告警
    ---
    tags:
      - 告警管理
    summary: 获取活跃告警
    description: 获取当前所有状态为triggered的活跃告警
    security:
      - SessionAuth: []
    produces:
      - application/json
    responses:
      200:
        description: 成功返回活跃告警列表
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: array
              items:
                type: object
            count:
              type: integer
              example: 3
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        alerts = AlertHistory.query.filter(
            AlertHistory.status == 'triggered'
        ).order_by(
            desc(AlertHistory.triggered_at)
        ).all()
        
        return jsonify({
            'success': True,
            'data': [alert.to_dict() for alert in alerts],
            'count': len(alerts)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

