#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据迁移服务
提供从SQLite到MySQL的数据迁移功能
"""
import os
import sys
import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import threading

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    import pymysql
    PYMYSQL_AVAILABLE = True
except ImportError:
    PYMYSQL_AVAILABLE = False

from app.services.database_config_service import get_database_config, validate_mysql_connection
from sqlalchemy import create_engine, inspect, text, MetaData, Table, Column, Integer, String, Text, Float, DateTime, Boolean, Date, LargeBinary
from sqlalchemy.schema import CreateTable
from sqlalchemy.engine import Engine


# 迁移状态（全局，用于跟踪迁移进度）
migration_status = {
    'status': 'idle',  # idle, running, completed, failed
    'progress': 0,
    'total_tables': 0,
    'current_table': '',
    'current_database': '',
    'message': '',
    'error': None,
    'started_at': None,
    'completed_at': None
}
migration_lock = threading.Lock()


def get_migration_status() -> Dict:
    """
    获取迁移状态
    
    Returns:
        dict: 迁移状态信息
    """
    with migration_lock:
        return migration_status.copy()


def reset_migration_status():
    """重置迁移状态"""
    global migration_status
    with migration_lock:
        migration_status = {
            'status': 'idle',
            'progress': 0,
            'total_tables': 0,
            'current_table': '',
            'current_database': '',
            'message': '',
            'error': None,
            'started_at': None,
            'completed_at': None
        }


def update_migration_status(**kwargs):
    """更新迁移状态"""
    global migration_status
    with migration_lock:
        migration_status.update(kwargs)


def get_sqlite_database_path(db_name: str = 'users') -> str:
    """
    获取SQLite数据库文件路径
    
    Args:
        db_name: 数据库名称（'users' 或 'traffic_data'）
        
    Returns:
        str: 数据库文件路径
    """
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    
    # Flask默认将数据库文件放在instance文件夹中
    instance_path = os.path.join(project_root, 'instance')
    if db_name == 'users':
        db_path = os.path.join(instance_path, 'users.db')
    else:
        db_path = os.path.join(instance_path, 'traffic_data.db')
    
    # 如果instance文件夹中不存在，尝试项目根目录
    if not os.path.exists(db_path):
        if db_name == 'users':
            db_path = os.path.join(project_root, 'users.db')
        else:
            db_path = os.path.join(project_root, 'traffic_data.db')
    
    return db_path


def create_mysql_engine(database_config: Dict, database_name: Optional[str] = None) -> Engine:
    """
    创建MySQL引擎
    
    Args:
        database_config: 数据库配置字典
        database_name: 数据库名称（如果为None，使用配置中的mysql_database）
        
    Returns:
        Engine: SQLAlchemy引擎
    """
    mysql_host = database_config.get('mysql_host', 'localhost')
    mysql_port = database_config.get('mysql_port', '3306')
    mysql_user = database_config.get('mysql_user', 'root')
    mysql_password = database_config.get('mysql_password', '')
    mysql_charset = database_config.get('mysql_charset', 'utf8mb4')
    
    if database_name is None:
        database_name = database_config.get('mysql_database', 'bandix_monitor')
    
    database_uri = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{database_name}?charset={mysql_charset}"
    return create_engine(database_uri, pool_pre_ping=True, pool_recycle=3600)


def ensure_mysql_database(database_config: Dict, database_name: str) -> bool:
    """
    确保MySQL数据库存在，如果不存在则创建
    
    Args:
        database_config: 数据库配置字典
        database_name: 数据库名称
        
    Returns:
        bool: 是否成功
    """
    try:
        mysql_host = database_config.get('mysql_host', 'localhost')
        mysql_port = int(database_config.get('mysql_port', '3306'))
        mysql_user = database_config.get('mysql_user', 'root')
        mysql_password = database_config.get('mysql_password', '')
        mysql_charset = database_config.get('mysql_charset', 'utf8mb4')
        
        # 连接到MySQL服务器（不指定数据库）
        connection = pymysql.connect(
            host=mysql_host,
            port=mysql_port,
            user=mysql_user,
            password=mysql_password,
            charset=mysql_charset,
            connect_timeout=5
        )
        
        try:
            with connection.cursor() as cursor:
                # 创建数据库（如果不存在）
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET {mysql_charset} COLLATE {mysql_charset}_unicode_ci")
                connection.commit()
            return True
        finally:
            connection.close()
    except Exception as e:
        print(f"创建MySQL数据库失败: {e}", file=sys.stderr)
        return False


def get_sqlite_tables(db_path: str) -> List[str]:
    """
    获取SQLite数据库中的所有表名
    
    Args:
        db_path: SQLite数据库文件路径
        
    Returns:
        list: 表名列表
    """
    if not os.path.exists(db_path):
        return []
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        return tables
    finally:
        conn.close()


def create_mysql_table_from_sqlite_reflection(sqlite_engine: Engine, mysql_engine: Engine, table_name: str) -> Tuple[bool, Optional[str]]:
    """
    使用SQLAlchemy反射从SQLite表创建MySQL表
    
    Args:
        sqlite_engine: SQLite引擎
        mysql_engine: MySQL引擎
        table_name: 表名
        
    Returns:
        tuple: (success, error_message)
    """
    try:
        # 从SQLite反射表结构
        sqlite_metadata = MetaData()
        sqlite_table = Table(table_name, sqlite_metadata, autoload_with=sqlite_engine)
        
        # 创建MySQL表的元数据
        mysql_metadata = MetaData()
        mysql_cols = []
        
        for col in sqlite_table.columns:
            # 转换数据类型
            col_type = col.type
            col_type_str = str(col_type).upper()
            
            # SQLite到MySQL类型映射
            if 'INTEGER' in col_type_str or 'INT' in col_type_str:
                mysql_type = Integer()
            elif 'TEXT' in col_type_str:
                mysql_type = Text()
            elif 'VARCHAR' in col_type_str or 'CHAR' in col_type_str:
                # 尝试获取长度
                length = None
                if hasattr(col_type, 'length') and col_type.length:
                    length = col_type.length
                elif 'VARCHAR' in col_type_str:
                    # 尝试从字符串中提取长度
                    import re
                    match = re.search(r'VARCHAR\((\d+)\)', col_type_str)
                    if match:
                        length = int(match.group(1))
                mysql_type = String(length=length) if length else String(255)
            elif 'REAL' in col_type_str or 'FLOAT' in col_type_str or 'DOUBLE' in col_type_str:
                mysql_type = Float()
            elif 'BLOB' in col_type_str:
                mysql_type = LargeBinary()
            elif 'DATETIME' in col_type_str or 'TIMESTAMP' in col_type_str:
                mysql_type = DateTime()
            elif 'DATE' in col_type_str:
                mysql_type = Date()
            elif 'BOOLEAN' in col_type_str or 'BOOL' in col_type_str:
                mysql_type = Boolean()
            else:
                # 默认使用Text
                mysql_type = Text()
            
            # 创建列，保留属性
            mysql_col = Column(
                col.name,
                mysql_type,
                primary_key=col.primary_key,
                nullable=col.nullable if not col.primary_key else False,
                unique=col.unique if hasattr(col, 'unique') else False
            )
            mysql_cols.append(mysql_col)
        
        # 创建MySQL表
        mysql_table = Table(table_name, mysql_metadata, *mysql_cols)
        
        # 在MySQL中创建表
        with mysql_engine.connect() as mysql_conn:
            # 删除已存在的表
            mysql_conn.execute(text(f"DROP TABLE IF EXISTS `{table_name}`"))
            mysql_conn.commit()
            
            # 生成CREATE TABLE语句
            create_stmt = CreateTable(mysql_table).compile(dialect=mysql_engine.dialect)
            mysql_conn.execute(text(str(create_stmt)))
            mysql_conn.commit()
        
        return True, None
        
    except Exception as e:
        import traceback
        error_msg = f"创建MySQL表 {table_name} 失败: {str(e)}\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr)
        return False, error_msg


def migrate_table_data(sqlite_conn: sqlite3.Connection, mysql_engine: Engine, table_name: str, batch_size: int = 1000) -> Tuple[bool, Optional[str], int]:
    """
    迁移单个表的数据
    
    Args:
        sqlite_conn: SQLite连接
        mysql_engine: MySQL引擎
        table_name: 表名
        batch_size: 批处理大小
        
    Returns:
        tuple: (success, error_message, row_count)
    """
    try:
        # 获取SQLite表的所有数据
        cursor = sqlite_conn.cursor()
        cursor.execute(f"SELECT * FROM `{table_name}`")
        columns = [description[0] for description in cursor.description]
        
        if not columns:
            return True, None, 0
        
        row_count = 0
        with mysql_engine.connect() as mysql_conn:
            # 清空MySQL表（如果已有数据）
            try:
                mysql_conn.execute(text(f"TRUNCATE TABLE `{table_name}`"))
                mysql_conn.commit()
            except Exception:
                # 如果表是空的或不存在，忽略错误
                pass
            
            # 批量插入数据
            batch = []
            for row in cursor.fetchall():
                # 将SQLite Row转换为元组
                if isinstance(row, sqlite3.Row):
                    row = tuple(row)
                batch.append(row)
                
                if len(batch) >= batch_size:
                    # 构建INSERT语句 - 使用VALUES子句列表进行批量插入
                    column_names = ','.join([f"`{col}`" for col in columns])
                    values_clauses = []
                    params = []
                    
                    for row_data in batch:
                        placeholders = ','.join(['%s'] * len(columns))
                        values_clauses.append(f"({placeholders})")
                        params.extend(row_data)
                    
                    insert_sql = f"INSERT INTO `{table_name}` ({column_names}) VALUES {','.join(values_clauses)}"
                    
                    try:
                        mysql_conn.execute(text(insert_sql), params)
                        mysql_conn.commit()
                        row_count += len(batch)
                    except Exception as e:
                        mysql_conn.rollback()
                        # 如果批量插入失败，尝试逐条插入
                        for single_row in batch:
                            try:
                                single_placeholders = ','.join(['%s'] * len(columns))
                                single_insert_sql = f"INSERT INTO `{table_name}` ({column_names}) VALUES ({single_placeholders})"
                                mysql_conn.execute(text(single_insert_sql), single_row)
                                mysql_conn.commit()
                                row_count += 1
                            except Exception as e2:
                                print(f"插入单行数据失败: {e2}, 数据: {single_row}", file=sys.stderr)
                        batch = []
                        continue
                    
                    batch = []
            
            # 插入剩余数据
            if batch:
                column_names = ','.join([f"`{col}`" for col in columns])
                values_clauses = []
                params = []
                
                for row_data in batch:
                    placeholders = ','.join(['%s'] * len(columns))
                    values_clauses.append(f"({placeholders})")
                    params.extend(row_data)
                
                insert_sql = f"INSERT INTO `{table_name}` ({column_names}) VALUES {','.join(values_clauses)}"
                
                try:
                    mysql_conn.execute(text(insert_sql), params)
                    mysql_conn.commit()
                    row_count += len(batch)
                except Exception as e:
                    mysql_conn.rollback()
                    # 如果批量插入失败，尝试逐条插入
                    for single_row in batch:
                        try:
                            single_placeholders = ','.join(['%s'] * len(columns))
                            single_insert_sql = f"INSERT INTO `{table_name}` ({column_names}) VALUES ({single_placeholders})"
                            mysql_conn.execute(text(single_insert_sql), single_row)
                            mysql_conn.commit()
                            row_count += 1
                        except Exception as e2:
                            print(f"插入单行数据失败: {e2}, 数据: {single_row}", file=sys.stderr)
        
        return True, None, row_count
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        return False, error_msg, 0


def migrate_database(db_name: str = 'users') -> Tuple[bool, Optional[str]]:
    """
    迁移整个数据库（从SQLite到MySQL）
    
    Args:
        db_name: 数据库名称（'users' 或 'traffic_data'）
        
    Returns:
        tuple: (success, error_message)
    """
    if not PYMYSQL_AVAILABLE:
        return False, "pymysql模块未安装，请运行: pip install pymysql"
    
    try:
        # 获取数据库配置
        database_config = get_database_config()
        
        # 验证MySQL连接
        is_valid, error_msg = validate_mysql_connection(database_config)
        if not is_valid:
            return False, error_msg
        
        # 确定MySQL数据库名称
        if db_name == 'users':
            mysql_db_name = database_config.get('mysql_database', 'bandix_monitor')
        else:
            mysql_db_name = database_config.get('mysql_traffic_database', database_config.get('mysql_database', 'bandix_monitor'))
        
        # 确保MySQL数据库存在
        if not ensure_mysql_database(database_config, mysql_db_name):
            return False, f"无法创建MySQL数据库: {mysql_db_name}"
        
        # 获取SQLite数据库路径
        sqlite_db_path = get_sqlite_database_path(db_name)
        if not os.path.exists(sqlite_db_path):
            return False, f"SQLite数据库文件不存在: {sqlite_db_path}"
        
        # 创建SQLite引擎
        sqlite_uri = f"sqlite:///{sqlite_db_path}"
        sqlite_engine = create_engine(sqlite_uri)
        
        # 创建MySQL引擎
        mysql_engine = create_mysql_engine(database_config, mysql_db_name)
        
        # 连接SQLite数据库（用于数据迁移）
        sqlite_conn = sqlite3.connect(sqlite_db_path)
        sqlite_conn.row_factory = sqlite3.Row
        
        try:
            # 获取所有表
            tables = get_sqlite_tables(sqlite_db_path)
            if not tables:
                return False, f"SQLite数据库中没有表: {db_name}"
            
            update_migration_status(
                status='running',
                total_tables=len(tables),
                current_database=db_name,
                message=f'开始迁移数据库: {db_name}，共 {len(tables)} 个表'
            )
            
            # 迁移每个表
            total_tables = len(tables)
            for idx, table_name in enumerate(tables):
                try:
                    # 更新进度（在表开始迁移时）
                    progress = int((idx / total_tables) * 100)
                    update_migration_status(
                        current_table=table_name,
                        progress=progress,
                        message=f'正在迁移表 {idx + 1}/{total_tables}: {table_name}'
                    )
                    
                    # 使用SQLAlchemy反射创建MySQL表
                    success, error_msg = create_mysql_table_from_sqlite_reflection(sqlite_engine, mysql_engine, table_name)
                    if not success:
                        return False, f"创建MySQL表 {table_name} 失败: {error_msg}"
                    
                    # 迁移数据
                    success, error_msg, row_count = migrate_table_data(sqlite_conn, mysql_engine, table_name)
                    if not success:
                        return False, f"迁移表 {table_name} 数据失败: {error_msg}"
                    
                    # 更新进度（表迁移完成后）
                    progress = int(((idx + 1) / total_tables) * 100)
                    update_migration_status(
                        progress=progress,
                        message=f'表 {table_name} 迁移完成，共 {row_count} 条记录（{idx + 1}/{total_tables}）'
                    )
                    
                except Exception as e:
                    import traceback
                    error_detail = f"{str(e)}\n{traceback.format_exc()}"
                    return False, f"迁移表 {table_name} 时发生错误: {error_detail}"
            
            update_migration_status(
                status='completed',
                progress=100,
                message=f'数据库 {db_name} 迁移完成',
                completed_at=datetime.now().isoformat()
            )
            
            return True, None
            
        finally:
            sqlite_conn.close()
            sqlite_engine.dispose()
            mysql_engine.dispose()
    
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        update_migration_status(
            status='failed',
            error=error_detail,
            message=f'迁移失败: {str(e)}',
            completed_at=datetime.now().isoformat()
        )
        return False, error_detail


def start_migration() -> Tuple[bool, Optional[str]]:
    """
    开始数据迁移（迁移所有数据库）
    
    Returns:
        tuple: (success, error_message)
    """
    global migration_status
    
    with migration_lock:
        if migration_status['status'] == 'running':
            return False, "迁移正在进行中，请等待完成"
        
        # 重置状态
        reset_migration_status()
        migration_status['status'] = 'running'
        migration_status['started_at'] = datetime.now().isoformat()
    
    try:
        # 迁移users数据库
        update_migration_status(message='开始迁移users数据库')
        success, error_msg = migrate_database('users')
        if not success:
            update_migration_status(
                status='failed',
                error=error_msg,
                message=f'迁移users数据库失败: {error_msg}',
                completed_at=datetime.now().isoformat()
            )
            return False, error_msg
        
        # 迁移traffic_data数据库
        update_migration_status(message='开始迁移traffic_data数据库')
        success, error_msg = migrate_database('traffic_data')
        if not success:
            update_migration_status(
                status='failed',
                error=error_msg,
                message=f'迁移traffic_data数据库失败: {error_msg}',
                completed_at=datetime.now().isoformat()
            )
            return False, error_msg
        
        update_migration_status(
            status='completed',
            progress=100,
            message='所有数据库迁移完成',
            completed_at=datetime.now().isoformat()
        )
        
        return True, None
        
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        update_migration_status(
            status='failed',
            error=error_detail,
            message=f'迁移过程发生错误: {str(e)}',
            completed_at=datetime.now().isoformat()
        )
        return False, error_detail
