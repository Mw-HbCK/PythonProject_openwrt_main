#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API调用统计API路由
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.api.user_api import admin_required
from app.services.api_stats_service import ApiStatsService

stats_bp = Blueprint('stats', __name__, url_prefix='/api/stats')


def parse_date_range():
    """
    解析请求中的日期范围参数
    
    Returns:
        tuple: (start_date, end_date) 或 (None, None)
    """
    start_date = None
    end_date = None
    
    # 从查询参数获取日期范围
    start_str = request.args.get('start_date')
    end_str = request.args.get('end_date')
    
    # 支持快捷时间范围（兼容time_range和range两种参数名）
    time_range = request.args.get('time_range') or request.args.get('range', 'all')
    
    if time_range == 'today':
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.utcnow()
    elif time_range == 'week':
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
    elif time_range == 'month':
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
    elif time_range == 'all':
        start_date = None
        end_date = None
    
    # 如果提供了具体的日期字符串，优先使用
    if start_str:
        try:
            start_date = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        except:
            pass
    
    if end_str:
        try:
            end_date = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
        except:
            pass
    
    return start_date, end_date


@stats_bp.route('/summary', methods=['GET'])
@admin_required
def get_summary():
    """
    获取统计摘要
    ---
    tags:
      - API统计
    summary: 获取API调用统计摘要
    description: 获取总调用次数、端点数量、活跃用户数等摘要信息
    security:
      - SessionAuth: []
    produces:
      - application/json
    parameters:
      - in: query
        name: range
        type: string
        enum: [today, week, month, all]
        default: all
        description: 时间范围（today=今日, week=本周, month=本月, all=全部）
      - in: query
        name: start_date
        type: string
        format: date-time
        description: 开始日期（ISO格式）
      - in: query
        name: end_date
        type: string
        format: date-time
        description: 结束日期（ISO格式）
    responses:
      200:
        description: 成功返回统计摘要
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                total_calls:
                  type: integer
                  example: 1500
                unique_endpoints:
                  type: integer
                  example: 25
                active_users:
                  type: integer
                  example: 5
      401:
        description: 未登录
      403:
        description: 需要管理员权限
      500:
        description: 服务器内部错误
    """
    try:
        start_date, end_date = parse_date_range()
        summary = ApiStatsService.get_summary(start_date, end_date)
        
        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stats_bp.route('/endpoints', methods=['GET'])
@admin_required
def get_endpoints():
    """
    获取所有端点的统计数据
    ---
    tags:
      - API统计
    summary: 获取所有端点的统计数据
    description: 获取所有API端点的调用统计信息
    security:
      - SessionAuth: []
    produces:
      - application/json
    parameters:
      - in: query
        name: range
        type: string
        enum: [today, week, month, all]
        default: all
        description: 时间范围
      - in: query
        name: start_date
        type: string
        format: date-time
        description: 开始日期
      - in: query
        name: end_date
        type: string
        format: date-time
        description: 结束日期
    responses:
      200:
        description: 成功返回端点统计列表
      401:
        description: 未登录
      403:
        description: 需要管理员权限
      500:
        description: 服务器内部错误
    """
    try:
        start_date, end_date = parse_date_range()
        stats = ApiStatsService.get_stats_by_endpoint(start_date, end_date)
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stats_bp.route('/endpoints/<path:endpoint>', methods=['GET'])
@admin_required
def get_endpoint_detail(endpoint):
    """
    获取特定端点的详细统计
    ---
    tags:
      - API统计
    summary: 获取特定端点的详细统计
    description: 获取指定API端点的详细统计信息，包括按方法、状态码、用户的分布
    security:
      - SessionAuth: []
    produces:
      - application/json
    parameters:
      - in: path
        name: endpoint
        type: string
        required: true
        description: API端点路径（如 /api/user/info）
      - in: query
        name: range
        type: string
        enum: [today, week, month, all]
        default: all
        description: 时间范围
      - in: query
        name: start_date
        type: string
        format: date-time
        description: 开始日期
      - in: query
        name: end_date
        type: string
        format: date-time
        description: 结束日期
    responses:
      200:
        description: 成功返回端点详细统计
      401:
        description: 未登录
      403:
        description: 需要管理员权限
      500:
        description: 服务器内部错误
    """
    try:
        # 确保endpoint以/开头
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        
        start_date, end_date = parse_date_range()
        detail = ApiStatsService.get_endpoint_detail(endpoint, start_date, end_date)
        
        return jsonify({
            'success': True,
            'data': detail
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stats_bp.route('/top', methods=['GET'])
@admin_required
def get_top_endpoints():
    """
    获取调用最多的端点（Top N）
    ---
    tags:
      - API统计
    summary: 获取调用最多的端点
    description: 获取调用次数最多的API端点列表
    security:
      - SessionAuth: []
    produces:
      - application/json
    parameters:
      - in: query
        name: limit
        type: integer
        default: 10
        description: 返回数量限制
      - in: query
        name: range
        type: string
        enum: [today, week, month, all]
        default: all
        description: 时间范围
      - in: query
        name: start_date
        type: string
        format: date-time
        description: 开始日期
      - in: query
        name: end_date
        type: string
        format: date-time
        description: 结束日期
    responses:
      200:
        description: 成功返回Top端点列表
      401:
        description: 未登录
      403:
        description: 需要管理员权限
      500:
        description: 服务器内部错误
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        if limit > 100:
            limit = 100  # 限制最大返回数量
        
        start_date, end_date = parse_date_range()
        top_endpoints = ApiStatsService.get_top_endpoints(limit, start_date, end_date)
        
        return jsonify({
            'success': True,
            'data': top_endpoints
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

