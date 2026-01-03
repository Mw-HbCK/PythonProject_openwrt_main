#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份管理API路由
"""
from flask import Blueprint, request, jsonify, send_file, session
from datetime import datetime
import os
import sys
import json
import shutil
import sqlite3

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.api.user_api import login_required, admin_required
from app.models.user_models import User, db as user_db
from app.models.backup_models import BackupHistory
from app.models.database_models import db as traffic_db
from app.services.backup_service import BackupService
from app.services.config_manager import load_config_file, save_config_file, validate_config, get_config_file_path
from app.services.backup_scheduler import get_backup_scheduler

backup_bp = Blueprint('backup', __name__, url_prefix='/api/backup')


@backup_bp.route('/history', methods=['GET'])
@login_required
def get_backup_history():
    """
    获取备份历史记录
    ---
    tags:
      - 备份管理
    summary: 获取备份历史记录列表
    description: 获取所有备份历史记录
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
    responses:
      200:
        description: 成功返回备份历史
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # 查询备份历史（按创建时间倒序）
        pagination = BackupHistory.query.order_by(BackupHistory.created_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        backups = [backup.to_dict() for backup in pagination.items]
        
        return jsonify({
            'success': True,
            'data': backups,
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


@backup_bp.route('/download/<int:backup_id>', methods=['GET'])
@login_required
def download_backup(backup_id):
    """
    下载备份文件
    ---
    tags:
      - 备份管理
    summary: 下载备份文件
    description: 下载指定ID的备份文件
    security:
      - SessionAuth: []
    parameters:
      - in: path
        name: backup_id
        type: integer
        required: true
        description: 备份记录ID
    responses:
      200:
        description: 成功返回备份文件
      404:
        description: 备份记录不存在
      401:
        description: 未登录
      500:
        description: 服务器内部错误
    """
    try:
        backup = BackupHistory.query.get(backup_id)
        if not backup:
            return jsonify({
                'success': False,
                'error': '备份记录不存在'
            }), 404
        
        if backup.status != 'success':
            return jsonify({
                'success': False,
                'error': '备份失败，无法下载'
            }), 400
        
        backup_path = backup.backup_path
        
        # 检查文件是否存在
        if not os.path.exists(backup_path):
            return jsonify({
                'success': False,
                'error': '备份文件不存在'
            }), 404
        
        # 如果是目录（未压缩），需要压缩后发送
        if os.path.isdir(backup_path):
            import zipfile
            import io
            
            # 在内存中创建ZIP文件，避免Windows文件锁定问题
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(backup_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, backup_path)
                        zipf.write(file_path, arcname)
            
            # 重置缓冲区位置到开始
            zip_buffer.seek(0)
            
            # 创建响应
            from flask import Response
            response = Response(
                zip_buffer.getvalue(),
                mimetype='application/zip',
                headers={
                    'Content-Disposition': f'attachment; filename="{backup.backup_filename}.zip"'
                }
            )
            return response
        else:
            # 直接发送ZIP文件
            return send_file(
                backup_path,
                mimetype='application/zip',
                as_attachment=True,
                download_name=backup.backup_filename
            )
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backup_bp.route('/manual', methods=['POST'])
@admin_required
def trigger_manual_backup():
    """
    手动触发备份
    ---
    tags:
      - 备份管理
    summary: 手动触发备份
    description: 立即执行一次备份任务
    security:
      - SessionAuth: []
    responses:
      200:
        description: 备份已启动
      401:
        description: 未登录
      403:
        description: 无权限
      500:
        description: 服务器内部错误
    """
    try:
        from flask import current_app
        
        # 在后台线程中执行备份
        import threading
        
        # 获取当前应用实例（在请求上下文中）
        app = current_app._get_current_object()
        
        def run_backup():
            try:
                with app.app_context():
                    backup_service = BackupService(app)
                    config_file = get_config_file_path()
                    _, _, _, _, backup_config, _, _, _ = load_config_file(config_file)
                    
                    backup_dir = backup_config.get('backup_dir', './backups')
                    databases_str = backup_config.get('databases', 'users,traffic')
                    # 去除注释（如果有）
                    if '#' in databases_str:
                        databases_str = databases_str.split('#')[0]
                    databases = [db.strip() for db in databases_str.split(',') if db.strip()]
                    compress = backup_config.get('compress', 'true').lower() == 'true'
                    keep_count_str = backup_config.get('keep_count', '30')
                    # 去除注释（如果有）
                    if '#' in keep_count_str:
                        keep_count_str = keep_count_str.split('#')[0]
                    keep_count = int(keep_count_str.strip())
                    
                    backup_path, backup_size, databases_backed_up = backup_service.backup_databases(
                        db_names=databases,
                        backup_dir=backup_dir,
                        compress=compress
                    )
                    
                    backup_filename = os.path.basename(backup_path)
                    
                    # 上传到云存储
                    cloud_uploaded = False
                    try:
                        cloud_uploaded = backup_service.upload_to_cloud(backup_path, backup_config)
                    except Exception as e:
                        print(f"[手动备份] 云存储上传失败: {e}", file=sys.stderr)
                    
                    # 记录备份历史
                    backup_record = BackupHistory(
                        backup_filename=backup_filename,
                        backup_path=backup_path,
                        backup_size=backup_size,
                        databases=json.dumps(databases_backed_up),
                        status='success',
                        cloud_uploaded=cloud_uploaded
                    )
                    user_db.session.add(backup_record)
                    user_db.session.commit()
                    
                    # 清理旧备份
                    try:
                        backup_service.delete_old_backups(backup_dir, keep_count)
                    except Exception as e:
                        print(f"[手动备份] 清理旧备份失败: {e}", file=sys.stderr)
                        
            except Exception as e:
                print(f"[手动备份] 备份失败: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                
                # 记录失败的备份
                try:
                    with app.app_context():
                        backup_record = BackupHistory(
                            backup_filename='',
                            backup_path='',
                            backup_size=0,
                            databases=json.dumps([]),
                            status='failed',
                            error_message=str(e),
                            cloud_uploaded=False
                        )
                        user_db.session.add(backup_record)
                        user_db.session.commit()
                except Exception:
                    pass
        
        thread = threading.Thread(target=run_backup, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': '备份任务已启动，将在后台执行'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backup_bp.route('/<int:backup_id>', methods=['DELETE'])
@admin_required
def delete_backup(backup_id):
    """
    删除备份文件
    ---
    tags:
      - 备份管理
    summary: 删除备份文件
    description: 删除指定的备份文件和记录（管理员）
    security:
      - SessionAuth: []
    parameters:
      - in: path
        name: backup_id
        type: integer
        required: true
        description: 备份记录ID
    responses:
      200:
        description: 删除成功
      404:
        description: 备份记录不存在
      401:
        description: 未登录
      403:
        description: 无权限
      500:
        description: 服务器内部错误
    """
    try:
        backup = BackupHistory.query.get(backup_id)
        if not backup:
            return jsonify({
                'success': False,
                'error': '备份记录不存在'
            }), 404
        
        backup_path = backup.backup_path
        
        # 删除文件或目录
        try:
            if os.path.exists(backup_path):
                if os.path.isdir(backup_path):
                    shutil.rmtree(backup_path)
                else:
                    os.remove(backup_path)
        except Exception as e:
            print(f"[删除备份] 删除文件失败: {e}", file=sys.stderr)
        
        # 删除数据库记录
        user_db.session.delete(backup)
        user_db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '备份已删除'
        })
        
    except Exception as e:
        user_db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backup_bp.route('/restore/<int:backup_id>', methods=['POST'])
@admin_required
def restore_backup(backup_id):
    """
    恢复备份（管理员）
    ---
    tags:
      - 备份管理
    summary: 恢复备份
    description: 从备份文件恢复数据库（管理员，危险操作）
    security:
      - SessionAuth: []
    parameters:
      - in: path
        name: backup_id
        type: integer
        required: true
        description: 备份记录ID
    responses:
      200:
        description: 恢复成功
      400:
        description: 请求错误
      401:
        description: 未登录
      403:
        description: 无权限
      500:
        description: 服务器内部错误
    """
    try:
        backup = BackupHistory.query.get(backup_id)
        if not backup:
            return jsonify({
                'success': False,
                'error': '备份记录不存在'
            }), 404
        
        if backup.status != 'success':
            return jsonify({
                'success': False,
                'error': '备份失败，无法恢复'
            }), 400
        
        backup_path = backup.backup_path
        if not os.path.exists(backup_path):
            return jsonify({
                'success': False,
                'error': '备份文件不存在'
            }), 404
        
        # 解析备份的数据库列表
        try:
            databases_list = json.loads(backup.databases) if backup.databases else []
        except:
            databases_list = []
        
        if not databases_list:
            return jsonify({
                'success': False,
                'error': '备份记录中没有数据库信息'
            }), 400
        
        # 恢复数据库
        from flask import current_app
        backup_service = BackupService(current_app)
        
        try:
            import zipfile
            import tempfile
            
            # 如果是ZIP文件，先解压
            if backup_path.endswith('.zip'):
                with tempfile.TemporaryDirectory() as temp_dir:
                    with zipfile.ZipFile(backup_path, 'r') as zipf:
                        zipf.extractall(temp_dir)
                    
                    # 恢复每个数据库
                    for db_name in databases_list:
                        sql_file = os.path.join(temp_dir, f"{db_name}.sql")
                        if os.path.exists(sql_file):
                            # 获取数据库路径
                            db_path = backup_service.get_database_path(db_name)
                            if db_path:
                                # 先备份当前数据库
                                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                                backup_current = f"{db_path}.backup.{timestamp}"
                                if os.path.exists(db_path):
                                    shutil.copy2(db_path, backup_current)
                                
                                # 读取SQL文件并执行
                                with open(sql_file, 'r', encoding='utf-8') as f:
                                    sql_content = f.read()
                                
                                # 删除旧数据库
                                if os.path.exists(db_path):
                                    os.remove(db_path)
                                
                                # 执行SQL恢复
                                conn = sqlite3.connect(db_path)
                                conn.executescript(sql_content)
                                conn.close()
                                
                                print(f"[恢复备份] 已恢复数据库: {db_name}")
            else:
                # 目录格式（未压缩）
                for db_name in databases_list:
                    sql_file = os.path.join(backup_path, f"{db_name}.sql")
                    if os.path.exists(sql_file):
                        db_path = backup_service.get_database_path(db_name)
                        if db_path:
                            # 先备份当前数据库
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            backup_current = f"{db_path}.backup.{timestamp}"
                            if os.path.exists(db_path):
                                shutil.copy2(db_path, backup_current)
                            
                            # 读取SQL文件并执行
                            with open(sql_file, 'r', encoding='utf-8') as f:
                                sql_content = f.read()
                            
                            # 删除旧数据库
                            if os.path.exists(db_path):
                                os.remove(db_path)
                            
                            # 执行SQL恢复
                            conn = sqlite3.connect(db_path)
                            conn.executescript(sql_content)
                            conn.close()
                            
                            print(f"[恢复备份] 已恢复数据库: {db_name}")
            
            return jsonify({
                'success': True,
                'message': '备份恢复成功，请重启服务'
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'恢复失败: {str(e)}'
            }), 500
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backup_bp.route('/config', methods=['GET'])
@login_required
def get_backup_config():
    """
    获取备份配置
    ---
    tags:
      - 备份管理
    summary: 获取备份配置
    description: 获取备份策略配置
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
        _, _, _, _, backup_config, _, _ = load_config_file(config_file)
        
        # 隐藏敏感信息
        display_config = backup_config.copy()
        user_id = session.get('user_id')
        is_admin = False
        if user_id:
            user = User.query.get(user_id)
            is_admin = user.is_admin() if user else False
        
        show_full = request.args.get('full', 'false').lower() == 'true' and is_admin
        if not show_full:
            if 'cloud_access_key' in display_config:
                display_config['cloud_access_key'] = '***'
            if 'cloud_secret_key' in display_config:
                display_config['cloud_secret_key'] = '***'
        
        return jsonify({
            'success': True,
            'data': display_config
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backup_bp.route('/config', methods=['PUT'])
@admin_required
def update_backup_config():
    """
    更新备份配置
    ---
    tags:
      - 备份管理
    summary: 更新备份配置
    description: 更新备份策略配置
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
        _, _, _, _, backup_config, _, _ = load_config_file(config_file)
        
        # 更新配置
        backup_config.update(data)
        
        # 验证配置
        is_valid, error_msg = validate_config(backup_config=backup_config)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # 保存配置
        save_config_file(backup_config=backup_config, config_file_path=config_file)
        
        # 重新加载调度器配置
        try:
            scheduler = get_backup_scheduler()
            if scheduler:
                scheduler.reload_config()
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"重新加载备份调度器配置失败: {e}", file=sys.stderr)
        
        return jsonify({
            'success': True,
            'message': '备份配置已更新'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backup_bp.route('/config/test', methods=['POST'])
@admin_required
def test_backup_config():
    """
    测试备份配置
    ---
    tags:
      - 备份管理
    summary: 测试备份配置
    description: 测试备份配置（测试云存储连接等）
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
        from flask import current_app
        config_file = get_config_file_path()
        _, _, _, _, backup_config, _, _ = load_config_file(config_file)
        
        results = {}
        
        # 测试备份目录
        backup_dir = backup_config.get('backup_dir', './backups')
        try:
            os.makedirs(backup_dir, exist_ok=True)
            test_file = os.path.join(backup_dir, '.test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            results['backup_dir'] = {'success': True, 'message': '备份目录可写'}
        except Exception as e:
            results['backup_dir'] = {'success': False, 'message': f'备份目录测试失败: {str(e)}'}
        
        # 测试云存储（如果启用）
        cloud_enabled = backup_config.get('cloud_enabled', 'false').lower() == 'true'
        if cloud_enabled:
            backup_service = BackupService(current_app)
            try:
                # 创建一个测试文件
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as test_file:
                    test_file.write(b'test')
                    test_file_path = test_file.name
                
                try:
                    uploaded = backup_service.upload_to_cloud(test_file_path, backup_config)
                    if uploaded:
                        results['cloud_storage'] = {'success': True, 'message': '云存储连接成功'}
                    else:
                        results['cloud_storage'] = {'success': False, 'message': '云存储上传失败'}
                finally:
                    if os.path.exists(test_file_path):
                        os.remove(test_file_path)
            except Exception as e:
                results['cloud_storage'] = {'success': False, 'message': f'云存储测试失败: {str(e)}'}
        
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

