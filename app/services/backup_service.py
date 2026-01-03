#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份服务
处理数据库备份、压缩、存储等操作
"""
import os
import sys
import sqlite3
import zipfile
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class BackupService:
    """备份服务类"""
    
    def __init__(self, app=None):
        """
        初始化备份服务
        
        Args:
            app: Flask应用实例（可选）
        """
        self.app = app
    
    def get_database_path(self, db_name: str) -> Optional[str]:
        """
        获取数据库文件路径
        
        Args:
            db_name: 数据库名称 ('users', 'traffic', 'alert_rules')
            
        Returns:
            str: 数据库文件路径，如果不存在返回None
        """
        try:
            # 获取项目根目录
            current_file = os.path.abspath(__file__)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
            instance_dir = os.path.join(project_root, 'instance')
            
            # 数据库文件名映射
            db_files = {
                'users': 'users.db',
                'traffic': 'traffic_data.db',
                'alert_rules': 'alert_rules.db'  # 告警数据实际上在traffic_data.db中
            }
            
            filename = db_files.get(db_name)
            if not filename:
                return None
            
            # 先尝试从Flask应用获取路径（如果有应用上下文）
            if self.app:
                try:
                    from flask import has_app_context, current_app
                    if has_app_context():
                        if db_name == 'users':
                            # 用户数据库
                            db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
                            if db_uri.startswith('sqlite:///'):
                                db_path = db_uri.replace('sqlite:///', '', 1)
                                if not os.path.isabs(db_path):
                                    instance_path = current_app.instance_path if hasattr(current_app, 'instance_path') else instance_dir
                                    db_path = os.path.join(instance_path, db_path)
                                if os.path.exists(db_path):
                                    return db_path
                        elif db_name == 'traffic':
                            # 流量数据库
                            from app.models.database_models import db
                            bind_key = 'traffic'
                            try:
                                engine = db.get_engine(current_app, bind=bind_key)
                                if engine:
                                    url = str(engine.url)
                                    if url.startswith('sqlite:///'):
                                        db_path = url.replace('sqlite:///', '', 1)
                                        if not os.path.isabs(db_path):
                                            instance_path = current_app.instance_path if hasattr(current_app, 'instance_path') else instance_dir
                                            db_path = os.path.join(instance_path, db_path)
                                        if os.path.exists(db_path):
                                            return db_path
                            except Exception:
                                pass
                except Exception:
                    pass
            
            # 默认路径查找
            db_path = os.path.join(instance_dir, filename)
            if os.path.exists(db_path):
                return db_path
            
            # 尝试项目根目录（向后兼容）
            root_path = os.path.join(project_root, filename)
            if os.path.exists(root_path):
                return root_path
            
            # 如果不存在，返回None（某些数据库可能不存在）
            return None
            
        except Exception as e:
            print(f"[备份服务] 获取数据库路径失败 {db_name}: {e}", file=sys.stderr)
            return None
    
    def export_database_sql(self, db_path: str) -> str:
        """
        导出数据库为SQL格式
        
        Args:
            db_path: 数据库文件路径
            
        Returns:
            str: SQL文件内容
        """
        try:
            if not os.path.exists(db_path):
                raise FileNotFoundError(f"数据库文件不存在: {db_path}")
            
            conn = sqlite3.connect(db_path)
            sql_dump = []
            
            # 导出所有表的数据
            for line in conn.iterdump():
                sql_dump.append(line)
            
            conn.close()
            
            return '\n'.join(sql_dump)
        except Exception as e:
            raise Exception(f"导出数据库失败 {db_path}: {str(e)}")
    
    def backup_databases(self, db_names: List[str], backup_dir: str, compress: bool = True) -> Tuple[str, int, List[str]]:
        """
        备份指定的数据库
        
        Args:
            db_names: 要备份的数据库名称列表 ['users', 'traffic', 'alert_rules']
            backup_dir: 备份文件存储目录
            compress: 是否压缩备份文件
            
        Returns:
            tuple: (backup_file_path, backup_size, databases_backed_up)
        """
        try:
            # 确保备份目录存在
            os.makedirs(backup_dir, exist_ok=True)
            
            # 生成备份文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            databases_backed_up = []
            sql_files = {}  # {db_name: sql_content}
            
            # 备份每个数据库
            for db_name in db_names:
                db_path = self.get_database_path(db_name)
                if db_path and os.path.exists(db_path):
                    try:
                        sql_content = self.export_database_sql(db_path)
                        sql_files[db_name] = sql_content
                        databases_backed_up.append(db_name)
                    except Exception as e:
                        print(f"[备份服务] 备份数据库 {db_name} 失败: {e}", file=sys.stderr)
                        # 继续备份其他数据库
                else:
                    print(f"[备份服务] 数据库 {db_name} 不存在，跳过", file=sys.stderr)
            
            if not databases_backed_up:
                raise Exception("没有成功备份任何数据库")
            
            if compress:
                # 压缩备份
                backup_filename = f"backup_{timestamp}.zip"
                backup_path = os.path.join(backup_dir, backup_filename)
                
                with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for db_name, sql_content in sql_files.items():
                        sql_filename = f"{db_name}.sql"
                        zipf.writestr(sql_filename, sql_content.encode('utf-8'))
                
                backup_size = os.path.getsize(backup_path)
            else:
                # 不压缩，创建目录存放多个SQL文件
                backup_dir_name = f"backup_{timestamp}"
                backup_full_dir = os.path.join(backup_dir, backup_dir_name)
                os.makedirs(backup_full_dir, exist_ok=True)
                
                total_size = 0
                for db_name, sql_content in sql_files.items():
                    sql_filename = os.path.join(backup_full_dir, f"{db_name}.sql")
                    with open(sql_filename, 'w', encoding='utf-8') as f:
                        f.write(sql_content)
                    total_size += os.path.getsize(sql_filename)
                
                # 创建一个标记文件
                info_file = os.path.join(backup_full_dir, 'backup_info.json')
                with open(info_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'timestamp': timestamp,
                        'databases': databases_backed_up
                    }, f, indent=2)
                
                backup_path = backup_full_dir
                backup_size = total_size
            
            return backup_path, backup_size, databases_backed_up
            
        except Exception as e:
            raise Exception(f"备份失败: {str(e)}")
    
    def get_backup_list(self, backup_dir: str) -> List[Dict[str, Any]]:
        """
        获取备份文件列表
        
        Args:
            backup_dir: 备份目录
            
        Returns:
            List[Dict]: 备份文件信息列表
        """
        backups = []
        
        try:
            if not os.path.exists(backup_dir):
                return backups
            
            for item in os.listdir(backup_dir):
                item_path = os.path.join(backup_dir, item)
                
                if os.path.isfile(item_path) and item.endswith('.zip'):
                    # ZIP文件
                    stat = os.stat(item_path)
                    backups.append({
                        'filename': item,
                        'path': item_path,
                        'size': stat.st_size,
                        'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'is_directory': False
                    })
                elif os.path.isdir(item_path) and item.startswith('backup_'):
                    # 备份目录（未压缩）
                    stat = os.stat(item_path)
                    # 计算目录总大小
                    total_size = 0
                    for root, dirs, files in os.walk(item_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            total_size += os.path.getsize(file_path)
                    
                    backups.append({
                        'filename': item,
                        'path': item_path,
                        'size': total_size,
                        'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'is_directory': True
                    })
            
            # 按创建时间倒序排序
            backups.sort(key=lambda x: x['created_at'], reverse=True)
            
        except Exception as e:
            print(f"[备份服务] 获取备份列表失败: {e}", file=sys.stderr)
        
        return backups
    
    def delete_old_backups(self, backup_dir: str, keep_count: int) -> int:
        """
        删除旧的备份文件，保留最近N个
        
        Args:
            backup_dir: 备份目录
            keep_count: 保留的备份数量
            
        Returns:
            int: 删除的备份数量
        """
        try:
            backups = self.get_backup_list(backup_dir)
            
            if len(backups) <= keep_count:
                return 0
            
            # 需要删除的备份（保留最新的keep_count个）
            to_delete = backups[keep_count:]
            deleted_count = 0
            
            for backup in to_delete:
                try:
                    if backup['is_directory']:
                        # 删除目录
                        import shutil
                        shutil.rmtree(backup['path'])
                    else:
                        # 删除文件
                        os.remove(backup['path'])
                    deleted_count += 1
                except Exception as e:
                    print(f"[备份服务] 删除备份失败 {backup['filename']}: {e}", file=sys.stderr)
            
            return deleted_count
            
        except Exception as e:
            print(f"[备份服务] 清理旧备份失败: {e}", file=sys.stderr)
            return 0
    
    def upload_to_cloud(self, backup_file: str, cloud_config: Dict[str, Any]) -> bool:
        """
        上传备份文件到云存储
        
        Args:
            backup_file: 备份文件路径
            cloud_config: 云存储配置
            
        Returns:
            bool: 是否上传成功
        """
        try:
            cloud_type = cloud_config.get('cloud_type', '').lower()
            cloud_enabled = cloud_config.get('cloud_enabled', 'false').lower() == 'true'
            
            if not cloud_enabled:
                return False
            
            if cloud_type == 's3':
                # AWS S3
                try:
                    import boto3
                    from botocore.exceptions import ClientError
                    
                    s3_client = boto3.client(
                        's3',
                        aws_access_key_id=cloud_config.get('cloud_access_key', ''),
                        aws_secret_access_key=cloud_config.get('cloud_secret_key', ''),
                        region_name=cloud_config.get('cloud_region', 'us-east-1')
                    )
                    
                    bucket_name = cloud_config.get('cloud_bucket', '')
                    if not bucket_name:
                        print("[备份服务] S3 bucket名称未配置", file=sys.stderr)
                        return False
                    
                    # 生成S3对象键（文件名）
                    backup_filename = os.path.basename(backup_file)
                    s3_key = f"backups/{backup_filename}"
                    
                    # 上传文件
                    s3_client.upload_file(backup_file, bucket_name, s3_key)
                    print(f"[备份服务] 成功上传到S3: s3://{bucket_name}/{s3_key}")
                    return True
                    
                except ImportError:
                    print("[备份服务] boto3未安装，无法上传到S3", file=sys.stderr)
                    return False
                except Exception as e:
                    print(f"[备份服务] 上传到S3失败: {e}", file=sys.stderr)
                    return False
                    
            elif cloud_type == 'oss':
                # 阿里云OSS
                try:
                    import oss2
                    
                    access_key = cloud_config.get('cloud_access_key', '')
                    secret_key = cloud_config.get('cloud_secret_key', '')
                    endpoint = cloud_config.get('cloud_endpoint', '')
                    bucket_name = cloud_config.get('cloud_bucket', '')
                    
                    if not all([access_key, secret_key, endpoint, bucket_name]):
                        print("[备份服务] OSS配置不完整", file=sys.stderr)
                        return False
                    
                    # 创建OSS客户端
                    auth = oss2.Auth(access_key, secret_key)
                    bucket = oss2.Bucket(auth, endpoint, bucket_name)
                    
                    # 生成OSS对象键
                    backup_filename = os.path.basename(backup_file)
                    oss_key = f"backups/{backup_filename}"
                    
                    # 上传文件
                    bucket.put_object_from_file(oss_key, backup_file)
                    print(f"[备份服务] 成功上传到OSS: {oss_key}")
                    return True
                    
                except ImportError:
                    print("[备份服务] oss2未安装，无法上传到OSS", file=sys.stderr)
                    return False
                except Exception as e:
                    print(f"[备份服务] 上传到OSS失败: {e}", file=sys.stderr)
                    return False
            else:
                print(f"[备份服务] 不支持的云存储类型: {cloud_type}", file=sys.stderr)
                return False
                
        except Exception as e:
            print(f"[备份服务] 云存储上传失败: {e}", file=sys.stderr)
            return False

