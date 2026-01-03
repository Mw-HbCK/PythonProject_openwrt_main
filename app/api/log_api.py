#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理API路由
"""
from flask import Blueprint, request, jsonify, send_file, session
from datetime import datetime
import os
import sys
import re
import gzip

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.api.user_api import login_required, admin_required
from app.models.user_models import User, db as user_db
from app.services.logger_service import get_logger_service
from app.services.config_manager import load_config_file, save_config_file, validate_config, get_config_file_path
from app.utils.logger import get_logger

log_bp = Blueprint('log', __name__, url_prefix='/api/logs')

# 获取日志记录器
logger = get_logger('log_api', category='business')
error_logger = get_logger('log_api', category='error')


@log_bp.route('/list', methods=['GET'])
@login_required
def get_log_files():
    """
    获取日志文件列表
    ---
    tags:
      - 日志管理
    summary: 获取日志文件列表
    description: 返回所有可用的日志文件及其信息
    security:
      - SessionAuth: []
    responses:
      200:
        description: 成功返回日志文件列表
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        service = get_logger_service()
        files = service.get_log_files()
        
        # 格式化文件大小
        for file_info in files:
            size = file_info['size']
            if size < 1024:
                file_info['size_formatted'] = f"{size} B"
            elif size < 1024 * 1024:
                file_info['size_formatted'] = f"{size / 1024:.2f} KB"
            else:
                file_info['size_formatted'] = f"{size / (1024 * 1024):.2f} MB"
        
        return jsonify({
            'success': True,
            'data': files
        })
    except Exception as e:
        error_logger.error(f"获取日志文件列表失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@log_bp.route('/view', methods=['GET'])
@login_required
def view_logs():
    """
    查看日志内容
    ---
    tags:
      - 日志管理
    summary: 查看日志内容
    description: 支持分页、搜索、过滤日志内容
    security:
      - SessionAuth: []
    parameters:
      - in: query
        name: file
        type: string
        description: 日志文件名
      - in: query
        name: page
        type: integer
        description: 页码（从1开始）
        default: 1
      - in: query
        name: per_page
        type: integer
        description: 每页行数
        default: 100
      - in: query
        name: level
        type: string
        description: 日志级别过滤 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
      - in: query
        name: search
        type: string
        description: 关键字搜索
      - in: query
        name: start_time
        type: string
        description: 开始时间 (ISO格式)
      - in: query
        name: end_time
        type: string
        description: 结束时间 (ISO格式)
    responses:
      200:
        description: 成功返回日志内容
      400:
        description: 请求参数错误
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        filename = request.args.get('file', '')
        if not filename:
            return jsonify({
                'success': False,
                'error': '缺少file参数'
            }), 400
        
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 100))
        level_filter = request.args.get('level', '').upper()
        search_keyword = request.args.get('search', '').strip()
        start_time = request.args.get('start_time', '')
        end_time = request.args.get('end_time', '')
        
        # 获取日志服务
        service = get_logger_service()
        if not service.log_dir:
            return jsonify({
                'success': False,
                'error': '日志目录未配置'
            }), 400
        
        # 构建文件路径
        if filename.startswith('archive/'):
            filepath = os.path.join(service.log_dir, filename)
        else:
            filepath = os.path.join(service.log_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': '日志文件不存在'
            }), 404
        
        # 读取日志文件
        lines = []
        try:
            # 判断是否是压缩文件
            if filename.endswith('.gz'):
                with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                    lines = f.readlines()
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
        except Exception as e:
            error_logger.error(f"读取日志文件失败: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'读取日志文件失败: {str(e)}'
            }), 500
        
        # 过滤日志
        filtered_lines = []
        for line in lines:
            line = line.rstrip('\n\r')
            if not line:
                continue
            
            # 级别过滤
            if level_filter:
                if level_filter not in line:
                    continue
            
            # 关键字搜索
            if search_keyword:
                if search_keyword.lower() not in line.lower():
                    continue
            
            # 时间过滤（简单实现，基于日志行中的时间戳）
            if start_time or end_time:
                # 尝试从日志行中提取时间戳
                # 这里假设日志格式包含时间戳
                time_match = re.search(r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})', line)
                if time_match:
                    log_time_str = time_match.group(1).replace(' ', 'T')
                    try:
                        log_time = datetime.fromisoformat(log_time_str)
                        if start_time:
                            start = datetime.fromisoformat(start_time.replace('Z', '+00:00').replace('+00:00', ''))
                            if log_time < start:
                                continue
                        if end_time:
                            end = datetime.fromisoformat(end_time.replace('Z', '+00:00').replace('+00:00', ''))
                            if log_time > end:
                                continue
                    except:
                        pass  # 如果时间解析失败，不过滤
            
            filtered_lines.append(line)
        
        # 分页
        total = len(filtered_lines)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_lines = filtered_lines[start_idx:end_idx]
        
        return jsonify({
            'success': True,
            'data': {
                'lines': paginated_lines,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        error_logger.error(f"查看日志失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@log_bp.route('/download/<path:filename>', methods=['GET'])
@login_required
def download_log(filename):
    """
    下载日志文件
    ---
    tags:
      - 日志管理
    summary: 下载日志文件
    description: 下载指定的日志文件
    security:
      - SessionAuth: []
    parameters:
      - in: path
        name: filename
        type: string
        required: true
        description: 日志文件名
    responses:
      200:
        description: 成功返回日志文件
      404:
        description: 日志文件不存在
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        service = get_logger_service()
        if not service.log_dir:
            return jsonify({
                'success': False,
                'error': '日志目录未配置'
            }), 400
        
        # 构建文件路径
        if filename.startswith('archive/'):
            filepath = os.path.join(service.log_dir, filename)
        else:
            filepath = os.path.join(service.log_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': '日志文件不存在'
            }), 404
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=os.path.basename(filename)
        )
        
    except Exception as e:
        error_logger.error(f"下载日志文件失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@log_bp.route('/clean', methods=['DELETE'])
@admin_required
def clean_logs():
    """
    清理旧日志
    ---
    tags:
      - 日志管理
    summary: 清理旧日志
    description: 删除旧的日志文件（管理员权限）
    security:
      - SessionAuth: []
    parameters:
      - in: query
        name: days
        type: integer
        description: 保留最近N天的日志
        default: 30
    responses:
      200:
        description: 清理成功
      401:
        description: 未登录
      403:
        description: 无权限
      500:
        description: 服务器内部错误
    """
    try:
        days = int(request.args.get('days', 30))
        
        service = get_logger_service()
        if not service.log_dir:
            return jsonify({
                'success': False,
                'error': '日志目录未配置'
            }), 400
        
        deleted_count = 0
        cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
        
        # 清理归档目录中的旧文件
        archive_dir = os.path.join(service.log_dir, 'archive')
        if os.path.exists(archive_dir):
            for filename in os.listdir(archive_dir):
                filepath = os.path.join(archive_dir, filename)
                if os.path.isfile(filepath):
                    file_mtime = os.path.getmtime(filepath)
                    if file_mtime < cutoff_time:
                        try:
                            os.remove(filepath)
                            deleted_count += 1
                        except Exception as e:
                            error_logger.warning(f"删除日志文件失败 {filepath}: {e}")
        
        logger.info(f"清理了 {deleted_count} 个旧日志文件（保留最近 {days} 天）")
        
        return jsonify({
            'success': True,
            'message': f'已清理 {deleted_count} 个旧日志文件',
            'data': {
                'deleted_count': deleted_count,
                'days': days
            }
        })
        
    except Exception as e:
        error_logger.error(f"清理日志失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@log_bp.route('/config', methods=['GET'])
@login_required
def get_log_config():
    """
    获取日志配置
    ---
    tags:
      - 日志管理
    summary: 获取日志配置
    description: 获取当前日志系统配置
    security:
      - SessionAuth: []
    responses:
      200:
        description: 成功返回日志配置
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        config_file = get_config_file_path()
        _, _, _, _, _, _, logging_config, _ = load_config_file(config_file)
        
        return jsonify({
            'success': True,
            'data': logging_config
        })
        
    except Exception as e:
        error_logger.error(f"获取日志配置失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@log_bp.route('/config', methods=['PUT'])
@admin_required
def update_log_config():
    """
    更新日志配置
    ---
    tags:
      - 日志管理
    summary: 更新日志配置
    description: 更新日志系统配置（管理员权限）
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
            log_level:
              type: string
            log_format:
              type: string
            log_dir:
              type: string
            log_max_bytes:
              type: integer
            log_backup_count:
              type: integer
            log_rotation:
              type: string
            log_to_console:
              type: boolean
            log_to_file:
              type: boolean
            log_categories:
              type: string
    responses:
      200:
        description: 配置更新成功
      400:
        description: 请求参数错误
      401:
        description: 未登录
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
        is_valid, error_msg = validate_config(logging_config=data)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # 保存配置
        config_file = get_config_file_path()
        bandix_config, api_config, collector_config, notifications_config, backup_config, report_config, _, _ = load_config_file(config_file)
        
        save_config_file(
            bandix_config=bandix_config,
            api_config=api_config,
            collector_config=collector_config,
            notifications_config=notifications_config,
            backup_config=backup_config,
            report_config=report_config,
            logging_config=data,
            database_config=None,
            config_file_path=config_file
        )
        
        # 重新初始化日志系统
        from app.services.logger_service import init_logging
        init_logging(data)
        
        logger.info("日志配置已更新")
        
        return jsonify({
            'success': True,
            'message': '日志配置已更新'
        })
        
    except Exception as e:
        error_logger.error(f"更新日志配置失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

