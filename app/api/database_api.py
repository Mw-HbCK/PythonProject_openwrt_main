#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库查询API
提供数据查询接口
"""
from flask import Blueprint, request, jsonify, send_file, has_app_context, current_app, session
from datetime import datetime, timedelta
from sqlalchemy import desc, and_, func, text
import os
import sys
import io

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.models.database_models import db, Device, TotalTraffic, DeviceTraffic
from app.api.user_api import login_required, admin_required
from app.models.user_models import User
from app.services.database_config_service import get_database_config

db_bp = Blueprint('database', __name__, url_prefix='/api/database')


@db_bp.route('/devices', methods=['GET'])
def get_devices():
    """
    获取所有设备列表
    ---
    tags:
      - 数据查询
    summary: 获取所有设备列表
    description: 获取数据库中所有设备的列表
    produces:
      - application/json
    responses:
      200:
        description: 成功返回设备列表
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
              example: 10
      500:
        description: 服务器内部错误
    """
    try:
        devices = Device.query.order_by(Device.created_at.desc()).all()
        return jsonify({
            'success': True,
            'data': [device.to_dict() for device in devices],
            'count': len(devices)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@db_bp.route('/total-traffic', methods=['GET'])
def get_total_traffic():
    """
    获取全网流量数据
    ---
    tags:
      - 数据查询
    summary: 获取全网流量数据
    description: 获取全网流量历史数据，支持分页和时间范围筛选
    produces:
      - application/json
    parameters:
      - in: query
        name: page
        type: integer
        description: 页码（从1开始，默认1）
        default: 1
      - in: query
        name: per_page
        type: integer
        description: 每页记录数（默认100，最大1000）
        default: 100
        maximum: 1000
      - in: query
        name: start_time
        type: string
        format: date-time
        description: 开始时间（ISO格式，可选）
      - in: query
        name: end_time
        type: string
        format: date-time
        description: 结束时间（ISO格式，可选）
    responses:
      200:
        description: 成功返回流量数据
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
                has_prev:
                  type: boolean
                has_next:
                  type: boolean
      500:
        description: 服务器内部错误
    """
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 100)), 1000)
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        query = TotalTraffic.query
        
        # 时间范围筛选
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                query = query.filter(TotalTraffic.timestamp >= start_dt)
            except:
                pass
        
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                query = query.filter(TotalTraffic.timestamp <= end_dt)
            except:
                pass
        
        # 按时间倒序排列
        query = query.order_by(desc(TotalTraffic.timestamp))
        
        # 分页
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'data': [record.to_dict() for record in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@db_bp.route('/device-traffic/<int:device_id>', methods=['GET'])
def get_device_traffic(device_id):
    """
    获取指定设备的流量数据
    ---
    tags:
      - 数据查询
    summary: 获取指定设备的流量数据
    description: 获取指定设备的流量历史数据，支持分页和时间范围筛选
    produces:
      - application/json
    parameters:
      - in: path
        name: device_id
        type: integer
        required: true
        description: 设备ID
      - in: query
        name: page
        type: integer
        description: 页码（从1开始，默认1）
        default: 1
      - in: query
        name: per_page
        type: integer
        description: 每页记录数（默认100，最大1000）
        default: 100
        maximum: 1000
      - in: query
        name: start_time
        type: string
        format: date-time
        description: 开始时间（ISO格式，可选）
      - in: query
        name: end_time
        type: string
        format: date-time
        description: 结束时间（ISO格式，可选）
    responses:
      200:
        description: 成功返回设备流量数据
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            device:
              type: object
            data:
              type: array
              items:
                type: object
            pagination:
              type: object
      404:
        description: 设备不存在
      500:
        description: 服务器内部错误
    """
    try:
        # 检查设备是否存在
        device = Device.query.get(device_id)
        if not device:
            return jsonify({
                'success': False,
                'error': '设备不存在'
            }), 404
        
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 100)), 1000)
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        query = DeviceTraffic.query.filter_by(device_id=device_id)
        
        # 时间范围筛选
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                query = query.filter(DeviceTraffic.timestamp >= start_dt)
            except:
                pass
        
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                query = query.filter(DeviceTraffic.timestamp <= end_dt)
            except:
                pass
        
        # 按时间倒序排列
        query = query.order_by(desc(DeviceTraffic.timestamp))
        
        # 分页（手动实现）
        total = query.count()
        total_pages = (total + per_page - 1) // per_page
        offset = (page - 1) * per_page
        items = query.offset(offset).limit(per_page).all()
        
        pagination = type('obj', (object,), {
            'items': items,
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages
        })()
        
        return jsonify({
            'success': True,
            'device': device.to_dict(),
            'data': [record.to_dict() for record in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@db_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    获取统计信息
    ---
    tags:
      - 数据查询
    summary: 获取统计信息
    description: 获取详细的统计信息，包括今日/本周/本月流量汇总、峰值速率、设备统计等
    produces:
      - application/json
    responses:
      200:
        description: 成功返回统计信息
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
      500:
        description: 服务器内部错误
    """
    try:
        now = datetime.utcnow()
        
        # 基础统计信息
        total_records = TotalTraffic.query.count()
        device_count = Device.query.count()
        device_traffic_records = DeviceTraffic.query.count()
        
        # 获取最新记录时间
        latest_total = TotalTraffic.query.order_by(desc(TotalTraffic.timestamp)).first()
        latest_device = DeviceTraffic.query.order_by(desc(DeviceTraffic.timestamp)).first()
        
        # 检查数据收集服务状态
        collector_status = "未知"
        collector_last_error = None
        try:
            from app.services.data_collector import IS_RUNNING, COLLECTOR_THREAD
            collector_status = "运行中" if IS_RUNNING else "已停止"
            if COLLECTOR_THREAD and not COLLECTOR_THREAD.is_alive() and IS_RUNNING:
                collector_status = "已停止（线程异常）"
        except Exception as e:
            collector_last_error = str(e)
        
        # 计算时间范围
        # 今日
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now
        
        # 本周
        days_since_monday = now.weekday()
        this_week_start = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        this_week_end = now
        
        # 本月
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month_end = now
        
        # 流量统计汇总
        traffic_summary = {
            'today': calculate_traffic_summary(today_start, today_end),
            'this_week': calculate_traffic_summary(this_week_start, this_week_end),
            'this_month': calculate_traffic_summary(this_month_start, this_month_end)
        }
        
        # 速率统计（使用今日数据）
        speed_stats = get_peak_speed(today_start, today_end)
        today_summary = traffic_summary['today']
        speed_stats['avg_down_speed_bytes'] = today_summary['avg_down_speed_bytes']
        speed_stats['avg_up_speed_bytes'] = today_summary['avg_up_speed_bytes']
        speed_stats['avg_down_speed_formatted'] = today_summary['avg_down_speed_formatted']
        speed_stats['avg_up_speed_formatted'] = today_summary['avg_up_speed_formatted']
        
        # 设备统计
        # 获取设备排名（基于今日数据）
        device_ranking = get_device_ranking(limit=10, start_time=today_start, end_time=today_end)
        
        # 计算设备流量占比（基于总流量）
        total_traffic_all = sum(d['total_traffic_bytes'] for d in device_ranking)
        device_distribution = []
        for device in device_ranking:
            percentage = (device['total_traffic_bytes'] / total_traffic_all * 100) if total_traffic_all > 0 else 0
            device_distribution.append({
                'device_id': device['device_id'],
                'device_name': device['device_name'],
                'mac': device['mac'],
                'total_traffic_bytes': device['total_traffic_bytes'],
                'total_traffic_formatted': device['total_traffic_formatted'],
                'percentage': round(percentage, 2)
            })
        
        # 活跃设备统计
        active_devices_24h = get_active_devices_count(hours=24)
        active_devices_7d = get_active_devices_count(hours=168)
        
        device_stats = {
            'ranking': device_ranking,
            'active_devices': {
                'last_24h': active_devices_24h,
                'last_7d': active_devices_7d
            },
            'traffic_distribution': device_distribution
        }
        
        # 时间段对比
        comparison = {
            'day_over_day': calculate_period_comparison('day'),
            'week_over_week': calculate_period_comparison('week'),
            'month_over_month': calculate_period_comparison('month')
        }
        
        stats = {
            # 基础统计（保持向后兼容）
            'total_traffic_records': total_records,
            'device_count': device_count,
            'device_traffic_records': device_traffic_records,
            'latest_total_traffic_time': latest_total.timestamp.isoformat() if latest_total else None,
            'latest_device_traffic_time': latest_device.timestamp.isoformat() if latest_device else None,
            'collector_status': collector_status,
            'collector_last_error': collector_last_error,
            # 新增详细统计
            'traffic_summary': traffic_summary,
            'speed_stats': speed_stats,
            'device_stats': device_stats,
            'comparison': comparison
        }
        
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


@db_bp.route('/charts/traffic-trend', methods=['GET'])
def get_traffic_trend():
    """
    获取流量趋势图数据
    ---
    tags:
      - 数据查询
    summary: 获取流量趋势图数据
    description: 获取流量趋势图表数据，支持全网或单个设备，支持时间范围和聚合间隔设置
    produces:
      - application/json
    parameters:
      - in: query
        name: type
        type: string
        enum: [total, device]
        description: 数据类型（默认total）
        default: total
      - in: query
        name: device_id
        type: integer
        description: 设备ID（type=device时必填）
      - in: query
        name: hours
        type: integer
        description: 时间范围（小时数，默认24，最大168）
        default: 24
        maximum: 168
      - in: query
        name: interval
        type: integer
        enum: [1, 5, 15, 30, 60]
        description: 聚合间隔（分钟，默认5）
        default: 5
    responses:
      200:
        description: 成功返回流量趋势数据
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
            meta:
              type: object
      400:
        description: 请求参数错误
      500:
        description: 服务器内部错误
    """
    try:
        data_type = request.args.get('type', 'total')  # total 或 device
        device_id = request.args.get('device_id', type=int)
        hours = min(int(request.args.get('hours', 24)), 168)  # 最大7天
        interval = int(request.args.get('interval', 5))  # 聚合间隔（分钟）
        
        # 计算时间范围
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # 构建查询
        if data_type == 'total':
            query = TotalTraffic.query.filter(
                TotalTraffic.timestamp >= start_time,
                TotalTraffic.timestamp <= end_time
            )
        else:  # device
            if not device_id:
                return jsonify({
                    'success': False,
                    'error': 'device_id参数是必需的'
                }), 400
            
            query = DeviceTraffic.query.filter(
                DeviceTraffic.device_id == device_id,
                DeviceTraffic.timestamp >= start_time,
                DeviceTraffic.timestamp <= end_time
            )
        
        # 获取所有数据
        if data_type == 'total':
            records = query.order_by(TotalTraffic.timestamp.asc()).all()
        else:
            records = query.order_by(DeviceTraffic.timestamp.asc()).all()
        
        # 按时间间隔聚合数据
        aggregated_data = []
        interval_seconds = interval * 60
        
        if records:
            # 按时间间隔分组
            current_interval_start = None
            interval_data = []
            
            for record in records:
                timestamp = record.timestamp
                timestamp_seconds = int(timestamp.timestamp())
                interval_start_seconds = (timestamp_seconds // interval_seconds) * interval_seconds
                
                if current_interval_start != interval_start_seconds:
                    # 保存上一个区间的聚合数据
                    if interval_data:
                        aggregated_data.append({
                            'timestamp': datetime.fromtimestamp(current_interval_start).isoformat(),
                            'down_speed': sum(r.down_speed_bytes for r in interval_data) // len(interval_data),
                            'up_speed': sum(r.up_speed_bytes for r in interval_data) // len(interval_data),
                            'total_download': max(r.total_download_bytes for r in interval_data),
                            'total_upload': max(r.total_upload_bytes for r in interval_data),
                        })
                    
                    # 开始新区间
                    current_interval_start = interval_start_seconds
                    interval_data = [record]
                else:
                    interval_data.append(record)
            
            # 处理最后一个区间
            if interval_data:
                aggregated_data.append({
                    'timestamp': datetime.fromtimestamp(current_interval_start).isoformat(),
                    'down_speed': sum(r.down_speed_bytes for r in interval_data) // len(interval_data),
                    'up_speed': sum(r.up_speed_bytes for r in interval_data) // len(interval_data),
                    'total_download': max(r.total_download_bytes for r in interval_data),
                    'total_upload': max(r.total_upload_bytes for r in interval_data),
                })
        
        return jsonify({
            'success': True,
            'data': aggregated_data,
            'meta': {
                'type': data_type,
                'device_id': device_id,
                'hours': hours,
                'interval_minutes': interval,
                'count': len(aggregated_data)
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@db_bp.route('/charts/device-comparison', methods=['GET'])
def get_device_comparison():
    """
    获取设备对比图数据
    ---
    tags:
      - 数据查询
    summary: 获取设备对比图数据
    description: 获取设备对比图表数据，支持速率对比和流量对比
    produces:
      - application/json
    parameters:
      - in: query
        name: hours
        type: integer
        description: 时间范围（小时数，默认24，最大168）
        default: 24
        maximum: 168
      - in: query
        name: type
        type: string
        enum: [speed, total]
        description: 对比类型（默认speed）
        default: speed
    responses:
      200:
        description: 成功返回设备对比数据
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
      500:
        description: 服务器内部错误
    """
    try:
        hours = min(int(request.args.get('hours', 24)), 168)
        comparison_type = request.args.get('type', 'speed')  # speed 或 total
        
        # 计算时间范围
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # 获取所有设备
        devices = Device.query.all()
        
        comparison_data = []
        for device in devices:
            # 获取该设备在时间范围内的流量数据
            device_traffic = DeviceTraffic.query.filter(
                DeviceTraffic.device_id == device.id,
                DeviceTraffic.timestamp >= start_time,
                DeviceTraffic.timestamp <= end_time
            ).all()
            
            if not device_traffic:
                continue
            
            if comparison_type == 'speed':
                # 计算平均速率
                avg_down = sum(t.down_speed_bytes for t in device_traffic) // len(device_traffic)
                avg_up = sum(t.up_speed_bytes for t in device_traffic) // len(device_traffic)
                
                comparison_data.append({
                    'device_id': device.id,
                    'device_name': device.hostname or device.mac,
                    'mac': device.mac,
                    'down_speed': avg_down,
                    'up_speed': avg_up,
                    'total_speed': avg_down + avg_up
                })
            else:  # total
                # 计算总流量（取最新的值）
                latest = max(device_traffic, key=lambda t: t.timestamp)
                first = min(device_traffic, key=lambda t: t.timestamp)
                
                total_download = latest.total_download_bytes - first.total_download_bytes
                total_upload = latest.total_upload_bytes - first.total_upload_bytes
                
                comparison_data.append({
                    'device_id': device.id,
                    'device_name': device.hostname or device.mac,
                    'mac': device.mac,
                    'total_download': max(0, total_download),
                    'total_upload': max(0, total_upload),
                    'total_traffic': max(0, total_download + total_upload)
                })
        
        # 按总流量排序
        if comparison_type == 'speed':
            comparison_data.sort(key=lambda x: x['total_speed'], reverse=True)
        else:
            comparison_data.sort(key=lambda x: x['total_traffic'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': comparison_data,
            'meta': {
                'type': comparison_type,
                'hours': hours,
                'count': len(comparison_data)
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@db_bp.route('/dashboard', methods=['GET'])
def get_dashboard_data():
    """
    获取仪表盘数据
    ---
    tags:
      - 数据查询
    summary: 获取仪表盘数据
    description: 获取实时监控仪表盘所需的数据，包括最新流量数据、设备状态、排行榜和系统状态
    produces:
      - application/json
    responses:
      200:
        description: 成功返回仪表盘数据
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                total_data:
                  type: object
                devices:
                  type: array
                top_devices:
                  type: array
                system_status:
                  type: object
      500:
        description: 服务器内部错误
    """
    try:
        # 获取最新全网流量数据
        latest_total = TotalTraffic.query.order_by(desc(TotalTraffic.timestamp)).first()
        
        total_data = None
        if latest_total:
            total_data = {
                'down_speed_bytes': latest_total.down_speed_bytes,
                'up_speed_bytes': latest_total.up_speed_bytes,
                'down_speed_formatted': latest_total.down_speed_formatted or convert_bytes_to_speed(latest_total.down_speed_bytes),
                'up_speed_formatted': latest_total.up_speed_formatted or convert_bytes_to_speed(latest_total.up_speed_bytes),
                'total_download_bytes': latest_total.total_download_bytes,
                'total_upload_bytes': latest_total.total_upload_bytes,
                'total_download_formatted': latest_total.total_download_formatted or convert_bytes_to_size(latest_total.total_download_bytes),
                'total_upload_formatted': latest_total.total_upload_formatted or convert_bytes_to_size(latest_total.total_upload_bytes),
                'timestamp': latest_total.timestamp.isoformat() if latest_total.timestamp else None
            }
        
        # 获取所有设备及其最新流量数据
        devices = Device.query.all()
        device_list = []
        online_threshold = datetime.utcnow() - timedelta(minutes=5)  # 5分钟内活跃视为在线
        
        for device in devices:
            # 获取设备最新流量记录
            latest_traffic = DeviceTraffic.query.filter_by(device_id=device.id)\
                .order_by(desc(DeviceTraffic.timestamp)).first()
            
            if latest_traffic:
                # 判断设备是否在线（基于最新记录时间）
                is_online = latest_traffic.timestamp >= online_threshold if latest_traffic.timestamp else False
                
                # 计算最近1小时的总流量（用于排行榜）
                one_hour_ago = datetime.utcnow() - timedelta(hours=1)
                old_traffic = DeviceTraffic.query.filter(
                    DeviceTraffic.device_id == device.id,
                    DeviceTraffic.timestamp <= one_hour_ago
                ).order_by(desc(DeviceTraffic.timestamp)).first()
                
                # 计算1小时内的流量增量
                traffic_increment = 0
                if old_traffic:
                    traffic_increment = (latest_traffic.total_download_bytes + latest_traffic.total_upload_bytes) - \
                                       (old_traffic.total_download_bytes + old_traffic.total_upload_bytes)
                    traffic_increment = max(0, traffic_increment)
                else:
                    # 如果没有1小时前的数据，使用总流量
                    traffic_increment = latest_traffic.total_download_bytes + latest_traffic.total_upload_bytes
                
                device_list.append({
                    'id': device.id,
                    'hostname': device.hostname or '未知',
                    'mac': device.mac,
                    'ip': device.ip or '-',
                    'is_online': is_online,
                    'down_speed_bytes': latest_traffic.down_speed_bytes,
                    'up_speed_bytes': latest_traffic.up_speed_bytes,
                    'down_speed_formatted': latest_traffic.down_speed_formatted or convert_bytes_to_speed(latest_traffic.down_speed_bytes),
                    'up_speed_formatted': latest_traffic.up_speed_formatted or convert_bytes_to_speed(latest_traffic.up_speed_bytes),
                    'total_download_bytes': latest_traffic.total_download_bytes,
                    'total_upload_bytes': latest_traffic.total_upload_bytes,
                    'total_traffic_bytes': latest_traffic.total_download_bytes + latest_traffic.total_upload_bytes,
                    'traffic_increment': traffic_increment,  # 用于排行榜排序
                    'last_active': latest_traffic.timestamp.isoformat() if latest_traffic.timestamp else None
                })
        
        # 按流量增量排序（排行榜）
        device_list.sort(key=lambda x: x['traffic_increment'], reverse=True)
        
        # 获取系统状态
        total_records = TotalTraffic.query.count()
        device_count = Device.query.count()
        device_traffic_records = DeviceTraffic.query.count()
        
        collector_status = "未知"
        try:
            from app.services.data_collector import IS_RUNNING, COLLECTOR_THREAD
            collector_status = "运行中" if IS_RUNNING else "已停止"
            if COLLECTOR_THREAD and not COLLECTOR_THREAD.is_alive() and IS_RUNNING:
                collector_status = "已停止（线程异常）"
        except:
            pass
        
        system_status = {
            'collector_status': collector_status,
            'total_records': total_records,
            'device_count': device_count,
            'device_traffic_records': device_traffic_records,
            'latest_data_time': latest_total.timestamp.isoformat() if latest_total and latest_total.timestamp else None
        }
        
        return jsonify({
            'success': True,
            'data': {
                'total': total_data,
                'devices': device_list,
                'system_status': system_status
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def convert_bytes_to_speed(bytes_per_second):
    """将字节/秒转换为可读的速度字符串"""
    if bytes_per_second < 1024:
        return f"{bytes_per_second} B/s"
    elif bytes_per_second < 1024 * 1024:
        return f"{bytes_per_second / 1024:.2f} KB/s"
    elif bytes_per_second < 1024 * 1024 * 1024:
        return f"{bytes_per_second / (1024 * 1024):.2f} MB/s"
    else:
        return f"{bytes_per_second / (1024 * 1024 * 1024):.2f} GB/s"


def convert_bytes_to_size(bytes_value):
    """将字节转换为可读的大小字符串"""
    if bytes_value < 1024:
        return f"{bytes_value} B"
    elif bytes_value < 1024 * 1024:
        return f"{bytes_value / 1024:.2f} KB"
    elif bytes_value < 1024 * 1024 * 1024:
        return f"{bytes_value / (1024 * 1024):.2f} MB"
    elif bytes_value < 1024 * 1024 * 1024 * 1024:
        return f"{bytes_value / (1024 * 1024 * 1024):.2f} GB"
    else:
        return f"{bytes_value / (1024 * 1024 * 1024 * 1024):.2f} TB"


def calculate_traffic_summary(start_time, end_time):
    """
    计算指定时间段的流量汇总
    
    Args:
        start_time: 开始时间
        end_time: 结束时间
    
    Returns:
        dict: 包含总流量、平均速率等统计信息
    """
    try:
        query = TotalTraffic.query.filter(
            TotalTraffic.timestamp >= start_time,
            TotalTraffic.timestamp <= end_time
        )
        
        # 获取首尾记录以计算流量增量
        first_record = query.order_by(TotalTraffic.timestamp.asc()).first()
        last_record = query.order_by(TotalTraffic.timestamp.desc()).first()
        
        # 计算总流量增量
        total_download = 0
        total_upload = 0
        if first_record and last_record:
            total_download = max(0, last_record.total_download_bytes - first_record.total_download_bytes)
            total_upload = max(0, last_record.total_upload_bytes - first_record.total_upload_bytes)
        
        # 计算平均速率
        records = query.all()
        avg_down_speed = 0
        avg_up_speed = 0
        if records:
            avg_down_speed = sum(r.down_speed_bytes for r in records) / len(records)
            avg_up_speed = sum(r.up_speed_bytes for r in records) / len(records)
        
        return {
            'total_download_bytes': total_download,
            'total_upload_bytes': total_upload,
            'total_traffic_bytes': total_download + total_upload,
            'total_download_formatted': convert_bytes_to_size(total_download),
            'total_upload_formatted': convert_bytes_to_size(total_upload),
            'total_traffic_formatted': convert_bytes_to_size(total_download + total_upload),
            'avg_down_speed_bytes': avg_down_speed,
            'avg_up_speed_bytes': avg_up_speed,
            'avg_down_speed_formatted': convert_bytes_to_speed(avg_down_speed),
            'avg_up_speed_formatted': convert_bytes_to_speed(avg_up_speed),
            'record_count': len(records)
        }
    except Exception as e:
        return {
            'total_download_bytes': 0,
            'total_upload_bytes': 0,
            'total_traffic_bytes': 0,
            'total_download_formatted': '0 B',
            'total_upload_formatted': '0 B',
            'total_traffic_formatted': '0 B',
            'avg_down_speed_bytes': 0,
            'avg_up_speed_bytes': 0,
            'avg_down_speed_formatted': '0 B/s',
            'avg_up_speed_formatted': '0 B/s',
            'record_count': 0
        }


def get_peak_speed(start_time, end_time):
    """
    获取指定时间段的峰值速率及时间
    
    Args:
        start_time: 开始时间
        end_time: 结束时间
    
    Returns:
        dict: 包含峰值速率及对应时间
    """
    try:
        query = TotalTraffic.query.filter(
            TotalTraffic.timestamp >= start_time,
            TotalTraffic.timestamp <= end_time
        )
        
        # 获取下行峰值
        peak_down_record = query.order_by(desc(TotalTraffic.down_speed_bytes)).first()
        # 获取上行峰值
        peak_up_record = query.order_by(desc(TotalTraffic.up_speed_bytes)).first()
        
        result = {
            'peak_down_speed_bytes': 0,
            'peak_down_speed_formatted': '0 B/s',
            'peak_down_speed_time': None,
            'peak_up_speed_bytes': 0,
            'peak_up_speed_formatted': '0 B/s',
            'peak_up_speed_time': None
        }
        
        if peak_down_record:
            result['peak_down_speed_bytes'] = peak_down_record.down_speed_bytes
            result['peak_down_speed_formatted'] = convert_bytes_to_speed(peak_down_record.down_speed_bytes)
            result['peak_down_speed_time'] = peak_down_record.timestamp.isoformat() if peak_down_record.timestamp else None
        
        if peak_up_record:
            result['peak_up_speed_bytes'] = peak_up_record.up_speed_bytes
            result['peak_up_speed_formatted'] = convert_bytes_to_speed(peak_up_record.up_speed_bytes)
            result['peak_up_speed_time'] = peak_up_record.timestamp.isoformat() if peak_up_record.timestamp else None
        
        return result
    except Exception as e:
        return {
            'peak_down_speed_bytes': 0,
            'peak_down_speed_formatted': '0 B/s',
            'peak_down_speed_time': None,
            'peak_up_speed_bytes': 0,
            'peak_up_speed_formatted': '0 B/s',
            'peak_up_speed_time': None
        }


def get_device_ranking(limit=10, start_time=None, end_time=None):
    """
    获取设备流量排名
    
    Args:
        limit: 返回的设备数量（默认10）
        start_time: 开始时间（可选）
        end_time: 结束时间（可选）
    
    Returns:
        list: 设备排名列表
    """
    try:
        devices = Device.query.all()
        ranking = []
        
        for device in devices:
            query = DeviceTraffic.query.filter_by(device_id=device.id)
            
            if start_time:
                query = query.filter(DeviceTraffic.timestamp >= start_time)
            if end_time:
                query = query.filter(DeviceTraffic.timestamp <= end_time)
            
            # 获取首尾记录计算流量增量
            first_record = query.order_by(DeviceTraffic.timestamp.asc()).first()
            last_record = query.order_by(DeviceTraffic.timestamp.desc()).first()
            
            if first_record and last_record:
                total_download = max(0, last_record.total_download_bytes - first_record.total_download_bytes)
                total_upload = max(0, last_record.total_upload_bytes - first_record.total_upload_bytes)
                total_traffic = total_download + total_upload
                
                ranking.append({
                    'device_id': device.id,
                    'device_name': device.hostname or '未知',
                    'mac': device.mac,
                    'ip': device.ip or '-',
                    'total_download_bytes': total_download,
                    'total_upload_bytes': total_upload,
                    'total_traffic_bytes': total_traffic,
                    'total_download_formatted': convert_bytes_to_size(total_download),
                    'total_upload_formatted': convert_bytes_to_size(total_upload),
                    'total_traffic_formatted': convert_bytes_to_size(total_traffic)
                })
        
        # 按总流量排序
        ranking.sort(key=lambda x: x['total_traffic_bytes'], reverse=True)
        
        return ranking[:limit]
    except Exception as e:
        return []


def get_active_devices_count(hours=24):
    """
    获取活跃设备数量
    
    Args:
        hours: 时间范围（小时数，默认24）
    
    Returns:
        dict: 活跃设备统计信息
    """
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # 获取在指定时间段内有流量记录的不同设备数量
        active_device_ids = db.session.query(DeviceTraffic.device_id)\
            .filter(
                DeviceTraffic.timestamp >= start_time,
                DeviceTraffic.timestamp <= end_time
            )\
            .distinct()\
            .all()
        
        active_count = len(active_device_ids)
        total_count = Device.query.count()
        
        return {
            'active_count': active_count,
            'total_count': total_count,
            'hours': hours
        }
    except Exception as e:
        return {
            'active_count': 0,
            'total_count': 0,
            'hours': hours
        }


def calculate_period_comparison(period='day'):
    """
    计算同比/环比数据
    
    Args:
        period: 时间段类型 ('day', 'week', 'month')
    
    Returns:
        dict: 对比数据（当前时间段 vs 上一个时间段）
    """
    try:
        now = datetime.utcnow()
        
        if period == 'day':
            # 今日 vs 昨日
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = now
            yesterday_start = today_start - timedelta(days=1)
            yesterday_end = today_start
            
            current_period = '今日'
            previous_period = '昨日'
        elif period == 'week':
            # 本周 vs 上周
            days_since_monday = now.weekday()
            this_week_start = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            this_week_end = now
            last_week_start = this_week_start - timedelta(days=7)
            last_week_end = this_week_start
            
            today_start = this_week_start
            today_end = this_week_end
            yesterday_start = last_week_start
            yesterday_end = last_week_end
            
            current_period = '本周'
            previous_period = '上周'
        else:  # month
            # 本月 vs 上月
            this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            this_month_end = now
            # 计算上月的开始和结束时间
            if now.month == 1:
                # 如果是1月，上个月是去年12月
                last_month_start = now.replace(year=now.year-1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)
                last_month_end = this_month_start - timedelta(microseconds=1)
            else:
                last_month_start = now.replace(month=now.month-1, day=1, hour=0, minute=0, second=0, microsecond=0)
                last_month_end = this_month_start - timedelta(microseconds=1)
            
            today_start = this_month_start
            today_end = this_month_end
            yesterday_start = last_month_start
            yesterday_end = last_month_end
            
            current_period = '本月'
            previous_period = '上月'
        
        # 计算当前时间段统计
        current_stats = calculate_traffic_summary(today_start, today_end)
        # 计算上一个时间段统计
        previous_stats = calculate_traffic_summary(yesterday_start, yesterday_end)
        
        # 计算增长率
        current_total = current_stats['total_traffic_bytes']
        previous_total = previous_stats['total_traffic_bytes']
        
        if previous_total > 0:
            growth_rate = ((current_total - previous_total) / previous_total) * 100
        else:
            growth_rate = 100 if current_total > 0 else 0
        
        return {
            'current_period': current_period,
            'previous_period': previous_period,
            'current': current_stats,
            'previous': previous_stats,
            'growth_rate': round(growth_rate, 2),
            'growth_formatted': f"{'+' if growth_rate >= 0 else ''}{growth_rate:.2f}%"
        }
    except Exception as e:
        return {
            'current_period': period,
            'previous_period': f'上一个{period}',
            'current': {'total_traffic_bytes': 0, 'total_traffic_formatted': '0 B'},
            'previous': {'total_traffic_bytes': 0, 'total_traffic_formatted': '0 B'},
            'growth_rate': 0,
            'growth_formatted': '0%'
        }


# ============ 数据管理功能 ============



def get_database_stats():
    """
    获取数据库统计信息
    """
    try:
        total_traffic_records = TotalTraffic.query.count()
        device_count = Device.query.count()
        device_traffic_records = DeviceTraffic.query.count()
        
        # MySQL数据库大小需要通过查询information_schema获取
        db_size = 0
        try:
            database_config = get_database_config()
            # 所有表都在mysql_database数据库中（bind_key只是SQLAlchemy的概念）
            mysql_database = database_config.get('mysql_database', 'bandix_monitor')
            
            # 查询MySQL数据库大小（单位：字节）
            query = text("""
                SELECT ROUND(SUM(data_length + index_length), 0) AS db_size
                FROM information_schema.tables 
                WHERE table_schema = :db_name
            """)
            result = db.session.execute(query, {'db_name': mysql_database}).fetchone()
            if result and result[0] is not None:
                # 处理Decimal类型，转换为int
                size_value = result[0]
                if hasattr(size_value, '__int__'):
                    db_size = int(size_value)
                else:
                    db_size = int(float(size_value))
        except Exception as e:
            # 如果查询失败，保持db_size为0（不打印错误，避免日志过多）
            db_size = 0
        
        # 获取最早和最晚的记录时间
        earliest_total = TotalTraffic.query.order_by(TotalTraffic.timestamp.asc()).first()
        latest_total = TotalTraffic.query.order_by(desc(TotalTraffic.timestamp)).first()
        earliest_device = DeviceTraffic.query.order_by(DeviceTraffic.timestamp.asc()).first()
        latest_device = DeviceTraffic.query.order_by(desc(DeviceTraffic.timestamp)).first()
        
        return {
            'database_size_bytes': db_size,
            'database_size_formatted': convert_bytes_to_size(db_size),
            'total_traffic_records': total_traffic_records,
            'device_count': device_count,
            'device_traffic_records': device_traffic_records,
            'earliest_total_traffic_time': earliest_total.timestamp.isoformat() if earliest_total else None,
            'latest_total_traffic_time': latest_total.timestamp.isoformat() if latest_total else None,
            'earliest_device_traffic_time': earliest_device.timestamp.isoformat() if earliest_device else None,
            'latest_device_traffic_time': latest_device.timestamp.isoformat() if latest_device else None
        }
    except Exception as e:
        return {
            'database_size_bytes': 0,
            'database_size_formatted': '0 B',
            'total_traffic_records': 0,
            'device_count': 0,
            'device_traffic_records': 0,
            'earliest_total_traffic_time': None,
            'latest_total_traffic_time': None,
            'earliest_device_traffic_time': None,
            'latest_device_traffic_time': None
        }


def cleanup_old_data(keep_days=None, start_time=None, end_time=None):
    """
    清理旧数据
    
    Args:
        keep_days: 保留最近N天的数据
        start_time: 开始时间（用于手动指定范围）
        end_time: 结束时间（用于手动指定范围）
    
    Returns:
        dict: 删除的记录数
    """
    try:
        deleted_total = 0
        deleted_device = 0
        
        if keep_days:
            # 按天数保留数据
            cutoff_time = datetime.utcnow() - timedelta(days=keep_days)
            
            # 删除TotalTraffic中的旧数据
            deleted_total = TotalTraffic.query.filter(TotalTraffic.timestamp < cutoff_time).delete()
            
            # 删除DeviceTraffic中的旧数据
            deleted_device = DeviceTraffic.query.filter(DeviceTraffic.timestamp < cutoff_time).delete()
            
        elif start_time and end_time:
            # 手动指定时间范围删除
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            # 删除指定时间范围内的数据
            deleted_total = TotalTraffic.query.filter(
                TotalTraffic.timestamp >= start_time,
                TotalTraffic.timestamp <= end_time
            ).delete()
            
            deleted_device = DeviceTraffic.query.filter(
                DeviceTraffic.timestamp >= start_time,
                DeviceTraffic.timestamp <= end_time
            ).delete()
        else:
            return {
                'deleted_total_traffic': 0,
                'deleted_device_traffic': 0,
                'total_deleted': 0
            }
        
        # 提交删除操作
        db.session.commit()
        
        return {
            'deleted_total_traffic': deleted_total,
            'deleted_device_traffic': deleted_device,
            'total_deleted': deleted_total + deleted_device
        }
    except Exception as e:
        db.session.rollback()
        raise e


def export_database_backup():
    """
    导出数据库为SQL格式（MySQL）
    
    Returns:
        str: SQL文件内容
    """
    try:
        # MySQL备份需要使用mysqldump或通过SQLAlchemy查询
        # 这里返回一个提示信息，实际备份应通过备份服务进行
        raise NotImplementedError("MySQL数据库备份应使用备份服务或mysqldump工具")
    except Exception as e:
        raise e


@db_bp.route('/management/stats', methods=['GET'])
def get_management_stats():
    """
    获取数据库管理统计信息
    ---
    tags:
      - 数据查询
    summary: 获取数据库管理统计信息
    description: 获取数据库的统计信息，包括数据库大小、记录数、设备数等
    produces:
      - application/json
    responses:
      200:
        description: 成功返回统计信息
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                database_size_bytes:
                  type: integer
                database_size_formatted:
                  type: string
                total_traffic_records:
                  type: integer
                device_traffic_records:
                  type: integer
                device_count:
                  type: integer
      500:
        description: 服务器内部错误
    """
    try:
        stats = get_database_stats()
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


@db_bp.route('/management/cleanup', methods=['POST'])
@login_required
@admin_required
def cleanup_data():
    """
    数据清理接口
    ---
    tags:
      - 数据查询
    summary: 数据清理
    description: 清理旧数据，支持按保留天数或时间范围删除，支持预览模式
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
            keep_days:
              type: integer
              description: 保留最近N天的数据
            start_time:
              type: string
              format: date-time
              description: 开始时间（ISO格式）
            end_time:
              type: string
              format: date-time
              description: 结束时间（ISO格式）
            preview:
              type: boolean
              description: 是否只是预览（默认false）
              default: false
    responses:
      200:
        description: 清理成功或预览结果
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            preview:
              type: boolean
            data:
              type: object
      400:
        description: 请求参数错误
      500:
        description: 服务器内部错误
    """
    try:
        data = request.get_json() or {}
        keep_days = data.get('keep_days', type=int)
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        preview = data.get('preview', False)
        
        if not keep_days and not (start_time and end_time):
            return jsonify({
                'success': False,
                'error': '必须提供keep_days或start_time和end_time参数'
            }), 400
        
        if preview:
            # 预览模式：计算将删除的记录数，但不实际删除
            if keep_days:
                cutoff_time = datetime.utcnow() - timedelta(days=keep_days)
                total_count = TotalTraffic.query.filter(TotalTraffic.timestamp < cutoff_time).count()
                device_count = DeviceTraffic.query.filter(DeviceTraffic.timestamp < cutoff_time).count()
            else:
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                if isinstance(end_time, str):
                    end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                total_count = TotalTraffic.query.filter(
                    TotalTraffic.timestamp >= start_time,
                    TotalTraffic.timestamp <= end_time
                ).count()
                device_count = DeviceTraffic.query.filter(
                    DeviceTraffic.timestamp >= start_time,
                    DeviceTraffic.timestamp <= end_time
                ).count()
            
            return jsonify({
                'success': True,
                'preview': True,
                'data': {
                    'will_delete_total_traffic': total_count,
                    'will_delete_device_traffic': device_count,
                    'total_will_delete': total_count + device_count
                }
            })
        else:
            # 执行实际删除
            result = cleanup_old_data(keep_days=keep_days, start_time=start_time, end_time=end_time)
            return jsonify({
                'success': True,
                'data': result
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@db_bp.route('/management/vacuum', methods=['POST'])
@login_required
@admin_required
def vacuum_database():
    """
    数据库优化接口
    ---
    tags:
      - 数据查询
    summary: 数据库优化
    description: 执行SQLite VACUUM命令优化数据库，回收未使用空间
    produces:
      - application/json
    responses:
      200:
        description: 优化成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                size_before_bytes:
                  type: integer
                size_after_bytes:
                  type: integer
                size_reduced_bytes:
                  type: integer
      500:
        description: 服务器内部错误
    """
    try:
        # 获取优化前的数据库大小
        stats_before = get_database_stats()
        size_before = stats_before['database_size_bytes']
        
        # 执行VACUUM
        db.session.execute(text('VACUUM'))
        db.session.commit()
        
        # 获取优化后的数据库大小
        stats_after = get_database_stats()
        size_after = stats_after['database_size_bytes']
        
        return jsonify({
            'success': True,
            'data': {
                'size_before_bytes': size_before,
                'size_before_formatted': convert_bytes_to_size(size_before),
                'size_after_bytes': size_after,
                'size_after_formatted': convert_bytes_to_size(size_after),
                'size_reduced_bytes': max(0, size_before - size_after),
                'size_reduced_formatted': convert_bytes_to_size(max(0, size_before - size_after))
            }
        })
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@db_bp.route('/management/backup', methods=['GET'])
@login_required
@admin_required
def backup_database():
    """
    导出数据库备份
    ---
    tags:
      - 数据查询
    summary: 导出数据库备份
    description: 导出数据库为SQL备份文件
    produces:
      - application/sql
      - application/json
    responses:
      200:
        description: 成功返回SQL备份文件
        schema:
          type: file
      500:
        description: 服务器内部错误
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: string
    """
    try:
        sql_content = export_database_backup()
        
        # 创建文件流
        output = io.BytesIO()
        output.write(sql_content.encode('utf-8'))
        output.seek(0)
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'traffic_data_backup_{timestamp}.sql'
        
        return send_file(
            output,
            mimetype='application/sql',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@db_bp.route('/management/backup-info', methods=['GET'])
def get_backup_info():
    """
    获取备份信息
    ---
    tags:
      - 数据查询
    summary: 获取备份信息
    description: 获取数据库备份相关信息，包括数据库大小、记录数等
    produces:
      - application/json
    responses:
      200:
        description: 成功返回备份信息
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                database_size_bytes:
                  type: integer
                database_size_formatted:
                  type: string
                total_traffic_records:
                  type: integer
                device_traffic_records:
                  type: integer
                device_count:
                  type: integer
      500:
        description: 服务器内部错误
    """
    try:
        stats = get_database_stats()
        return jsonify({
            'success': True,
            'data': {
                'database_size_bytes': stats['database_size_bytes'],
                'database_size_formatted': stats['database_size_formatted'],
                'total_traffic_records': stats['total_traffic_records'],
                'device_traffic_records': stats['device_traffic_records'],
                'device_count': stats['device_count'],
                'latest_total_traffic_time': stats['latest_total_traffic_time'],
                'latest_device_traffic_time': stats['latest_device_traffic_time']
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
