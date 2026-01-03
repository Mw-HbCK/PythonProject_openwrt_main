#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报表管理API路由
"""
from flask import Blueprint, request, jsonify, send_file, session, current_app
from datetime import datetime, timedelta
import os
import sys
import threading

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.api.user_api import login_required, admin_required
from app.models.user_models import User, db as user_db
from app.models.report_models import ReportHistory
from app.services.report_service import ReportService
from app.services.config_manager import load_config_file, save_config_file, validate_config, get_config_file_path

report_bp = Blueprint('report', __name__, url_prefix='/api/report')


@report_bp.route('/history', methods=['GET'])
@login_required
def get_report_history():
    """
    获取报表历史记录
    ---
    tags:
      - 报表管理
    summary: 获取报表历史记录列表
    description: 获取所有报表历史记录，支持分页和类型筛选
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
        description: 每页记录数
        default: 20
      - in: query
        name: report_type
        type: string
        enum: [daily, weekly, monthly]
        description: 报表类型筛选（可选）
    responses:
      200:
        description: 成功返回报表历史
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        report_type = request.args.get('report_type')
        
        # 构建查询
        query = ReportHistory.query
        
        # 类型筛选
        if report_type:
            query = query.filter(ReportHistory.report_type == report_type)
        
        # 查询报表历史（按创建时间倒序）
        pagination = query.order_by(ReportHistory.created_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        reports = [report.to_dict() for report in pagination.items]
        
        return jsonify({
            'success': True,
            'data': reports,
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


@report_bp.route('/download/<int:report_id>', methods=['GET'])
@login_required
def download_report(report_id):
    """
    下载报表文件
    ---
    tags:
      - 报表管理
    summary: 下载报表文件
    description: 下载指定ID的报表文件，支持PDF/HTML/Excel格式
    security:
      - SessionAuth: []
    parameters:
      - in: path
        name: report_id
        type: integer
        required: true
        description: 报表记录ID
      - in: query
        name: format
        type: string
        enum: [pdf, html, excel]
        description: 报表格式（默认pdf）
        default: pdf
    responses:
      200:
        description: 成功返回报表文件
      404:
        description: 报表记录不存在或文件不存在
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        report = ReportHistory.query.get(report_id)
        if not report:
            return jsonify({
                'success': False,
                'error': '报表记录不存在'
            }), 404
        
        if report.status != 'success':
            return jsonify({
                'success': False,
                'error': '报表生成失败，无法下载'
            }), 400
        
        # 获取格式参数
        format_type = request.args.get('format', 'pdf').lower()
        
        # 确定文件路径
        file_path = None
        mimetype = None
        download_name = None
        
        if format_type == 'pdf' and report.file_path_pdf:
            file_path = report.file_path_pdf
            mimetype = 'application/pdf'
            download_name = os.path.basename(file_path)
        elif format_type == 'html' and report.file_path_html:
            file_path = report.file_path_html
            mimetype = 'text/html'
            download_name = os.path.basename(file_path)
        elif format_type == 'excel' and report.file_path_excel:
            file_path = report.file_path_excel
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            download_name = os.path.basename(file_path)
        else:
            return jsonify({
                'success': False,
                'error': f'该格式的报表文件不存在: {format_type}'
            }), 404
        
        # 如果文件路径是相对路径，尝试转换为绝对路径
        if not os.path.isabs(file_path):
            # 获取项目根目录
            current_file = os.path.abspath(__file__)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
            # 处理相对路径，移除开头的./
            if file_path.startswith('./'):
                file_path = file_path[2:]
            file_path = os.path.join(project_root, file_path)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': f'报表文件不存在: {file_path}'
            }), 404
        
        # 发送文件
        return send_file(
            file_path,
            mimetype=mimetype,
            as_attachment=True,
            download_name=download_name
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@report_bp.route('/manual', methods=['POST'])
@admin_required
def trigger_manual_report():
    """
    手动触发报表生成
    ---
    tags:
      - 报表管理
    summary: 手动触发报表生成
    description: 立即执行一次报表生成任务（管理员）
    security:
      - SessionAuth: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            report_type:
              type: string
              enum: [daily, weekly, monthly]
              description: 报表类型
              required: true
            period_start:
              type: string
              format: date-time
              description: 报表周期开始时间（ISO格式，可选）
            period_end:
              type: string
              format: date-time
              description: 报表周期结束时间（ISO格式，可选）
    responses:
      200:
        description: 报表生成已启动
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
        data = request.get_json() or {}
        report_type = data.get('report_type')
        
        if not report_type or report_type not in ['daily', 'weekly', 'monthly']:
            return jsonify({
                'success': False,
                'error': 'report_type参数无效，必须是daily/weekly/monthly之一'
            }), 400
        
        # 解析时间范围（如果提供）
        period_start = None
        period_end = None
        
        if data.get('period_start'):
            try:
                period_start = datetime.fromisoformat(data['period_start'].replace('Z', '+00:00'))
            except:
                pass
        
        if data.get('period_end'):
            try:
                period_end = datetime.fromisoformat(data['period_end'].replace('Z', '+00:00'))
            except:
                pass
        
        # 如果没有提供时间范围，根据报表类型自动计算
        now = datetime.utcnow()
        if not period_start or not period_end:
            if report_type == 'daily':
                # 日报：昨天
                period_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                period_end = period_start + timedelta(days=1) - timedelta(seconds=1)
            elif report_type == 'weekly':
                # 周报：上周
                days_since_monday = now.weekday()
                last_week_start = (now - timedelta(days=days_since_monday + 7)).replace(hour=0, minute=0, second=0, microsecond=0)
                period_start = last_week_start
                period_end = last_week_start + timedelta(days=7) - timedelta(seconds=1)
            elif report_type == 'monthly':
                # 月报：上个月
                if now.month == 1:
                    period_start = now.replace(year=now.year-1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)
                else:
                    period_start = now.replace(month=now.month-1, day=1, hour=0, minute=0, second=0, microsecond=0)
                # 计算上个月的最后一天
                if period_start.month == 12:
                    period_end = period_start.replace(year=period_start.year+1, month=1, day=1) - timedelta(seconds=1)
                else:
                    period_end = period_start.replace(month=period_start.month+1, day=1) - timedelta(seconds=1)
        
        # 在后台线程中执行报表生成
        app = current_app._get_current_object()
        
        def run_report():
            try:
                with app.app_context():
                    # 加载报表配置
                    config_file = get_config_file_path()
                    _, _, _, _, _, report_config, _, _ = load_config_file(config_file)
                    # 如果report_config为空，使用默认配置
                    if not report_config:
                        report_config = {
                            'report_dir': './reports',
                            'generate_pdf': 'true',
                            'generate_html': 'true',
                            'generate_excel': 'true',
                            'pdf_library': 'reportlab'
                        }
                    
                    report_service = ReportService(app)
                    
                    # 生成报表
                    file_paths, total_size = report_service.generate_report(
                        report_type=report_type,
                        period_start=period_start,
                        period_end=period_end,
                        report_config=report_config
                    )
                    
                    # 生成报表周期字符串
                    period_str = period_start.strftime('%Y%m%d')
                    if report_type == 'weekly':
                        period_str = period_start.strftime('%Y%m%d')
                    elif report_type == 'monthly':
                        period_str = period_start.strftime('%Y%m')
                    
                    # 记录报表历史
                    report_record = ReportHistory(
                        report_type=report_type,
                        report_period=period_str,
                        file_path_pdf=file_paths.get('pdf'),
                        file_path_html=file_paths.get('html'),
                        file_path_excel=file_paths.get('excel'),
                        file_size=total_size,
                        status='success'
                    )
                    user_db.session.add(report_record)
                    user_db.session.commit()
                    
                    print(f"[手动报表] 报表生成成功: {report_type}, 周期: {period_str}")
                    
            except Exception as e:
                print(f"[手动报表] 报表生成失败: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                
                # 记录失败的报表
                try:
                    with app.app_context():
                        period_str = period_start.strftime('%Y%m%d') if period_start else 'unknown'
                        report_record = ReportHistory(
                            report_type=report_type,
                            report_period=period_str,
                            file_path_pdf=None,
                            file_path_html=None,
                            file_path_excel=None,
                            file_size=0,
                            status='failed',
                            error_message=str(e)
                        )
                        user_db.session.add(report_record)
                        user_db.session.commit()
                except Exception:
                    pass
        
        thread = threading.Thread(target=run_report, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': '报表生成任务已启动，将在后台执行'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@report_bp.route('/<int:report_id>', methods=['DELETE'])
@admin_required
def delete_report(report_id):
    """
    删除报表文件
    ---
    tags:
      - 报表管理
    summary: 删除报表文件
    description: 删除指定的报表文件和记录（管理员）
    security:
      - SessionAuth: []
    parameters:
      - in: path
        name: report_id
        type: integer
        required: true
        description: 报表记录ID
    responses:
      200:
        description: 删除成功
      404:
        description: 报表记录不存在
      401:
        description: 未登录
      403:
        description: 无权限
      500:
        description: 服务器内部错误
    """
    try:
        report = ReportHistory.query.get(report_id)
        if not report:
            return jsonify({
                'success': False,
                'error': '报表记录不存在'
            }), 404
        
        # 删除文件
        import shutil
        files_to_delete = []
        
        # 辅助函数：将相对路径转换为绝对路径
        def resolve_path(path):
            if not path:
                return None
            if os.path.isabs(path):
                return path
            # 获取项目根目录
            current_file = os.path.abspath(__file__)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
            # 处理相对路径，移除开头的./
            if path.startswith('./'):
                path = path[2:]
            return os.path.join(project_root, path)
        
        if report.file_path_pdf:
            pdf_path = resolve_path(report.file_path_pdf)
            if pdf_path and os.path.exists(pdf_path):
                files_to_delete.append(pdf_path)
        if report.file_path_html:
            html_path = resolve_path(report.file_path_html)
            if html_path and os.path.exists(html_path):
                files_to_delete.append(html_path)
        if report.file_path_excel:
            excel_path = resolve_path(report.file_path_excel)
            if excel_path and os.path.exists(excel_path):
                files_to_delete.append(excel_path)
        
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"[删除报表] 删除文件失败 {file_path}: {e}", file=sys.stderr)
        
        # 删除数据库记录
        user_db.session.delete(report)
        user_db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '报表已删除'
        })
        
    except Exception as e:
        user_db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@report_bp.route('/config', methods=['GET'])
@login_required
def get_report_config():
    """
    获取报表配置
    ---
    tags:
      - 报表管理
    summary: 获取报表配置
    description: 获取报表生成策略配置
    security:
      - SessionAuth: []
    produces:
      - application/json
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
        _, _, _, _, _, report_config, _ = load_config_file(config_file)
        
        return jsonify({
            'success': True,
            'data': report_config
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@report_bp.route('/config', methods=['PUT'])
@admin_required
def update_report_config():
    """
    更新报表配置
    ---
    tags:
      - 报表管理
    summary: 更新报表配置
    description: 更新报表生成策略配置（管理员）
    security:
      - SessionAuth: []
    consumes:
      - application/json
    produces:
      - application/json
    responses:
      200:
        description: 更新成功
      400:
        description: 请求参数错误或验证失败
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
        
        config_file = get_config_file_path()
        
        # 验证配置
        is_valid, error_msg = validate_config(report_config=data)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # 保存配置
        try:
            save_config_file(report_config=data, config_file_path=config_file)
        except Exception as e:
            print(f"[报表配置] 保存配置失败: {e}", file=sys.stderr)
            return jsonify({
                'success': False,
                'error': f'保存配置失败: {str(e)}'
            }), 500
        
        # 重新加载调度器配置
        try:
            from app.services.report_scheduler import get_report_scheduler
            scheduler = get_report_scheduler()
            if scheduler:
                scheduler.reload_config()
        except Exception as e:
            print(f"重新加载报表调度器配置失败: {e}", file=sys.stderr)
        
        return jsonify({
            'success': True,
            'message': '报表配置已更新'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@report_bp.route('/config/test', methods=['POST'])
@admin_required
def test_report_config():
    """
    测试报表配置
    ---
    tags:
      - 报表管理
    summary: 测试报表配置
    description: 测试报表配置（测试目录写入权限等）
    security:
      - SessionAuth: []
    responses:
      200:
        description: 测试完成
      401:
        description: 未登录
      403:
        description: 无权限
      500:
        description: 服务器内部错误
    """
    try:
        config_file = get_config_file_path()
        try:
            _, _, _, _, _, report_config, _ = load_config_file(config_file)
        except:
            report_config = {}
        
        results = {}
        
        # 测试报表目录
        report_dir = report_config.get('report_dir', './reports')
        try:
            os.makedirs(report_dir, exist_ok=True)
            test_file = os.path.join(report_dir, '.test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            results['report_dir'] = {'success': True, 'message': '报表目录可写'}
        except Exception as e:
            results['report_dir'] = {'success': False, 'message': f'报表目录测试失败: {str(e)}'}
        
        all_success = all(r.get('success', False) for r in results.values())
        
        return jsonify({
            'success': all_success,
            'message': '配置测试完成',
            'results': results
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

