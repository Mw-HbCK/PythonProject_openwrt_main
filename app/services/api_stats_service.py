#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API调用统计服务
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import func, and_, or_

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.models.api_stats_models import ApiCallStat, db
from app.models.user_models import User


class ApiStatsService:
    """API统计服务类"""
    
    @staticmethod
    def record_api_call(endpoint: str, method: str, user_id: Optional[int] = None, 
                       status_code: int = 200, username: Optional[str] = None):
        """
        记录API调用
        
        Args:
            endpoint: API端点路径
            method: HTTP方法
            user_id: 用户ID（可选）
            status_code: HTTP状态码
            username: 用户名（可选，如果提供则使用，否则从user_id查询）
        """
        try:
            # 如果提供了user_id但没有username，尝试查询用户名
            if user_id and not username:
                try:
                    user = User.query.get(user_id)
                    if user:
                        username = user.username
                except:
                    pass
            
            # 查找或创建统计记录
            # 使用(endpoint, method, user_id, status_code)作为唯一键
            stat = ApiCallStat.query.filter_by(
                endpoint=endpoint,
                method=method,
                user_id=user_id,
                status_code=status_code
            ).first()
            
            if stat:
                # 更新现有记录
                stat.call_count += 1
                stat.last_called_at = datetime.utcnow()
                stat.updated_at = datetime.utcnow()
                if username:
                    stat.username = username
            else:
                # 创建新记录
                stat = ApiCallStat(
                    endpoint=endpoint,
                    method=method,
                    user_id=user_id,
                    username=username,
                    status_code=status_code,
                    call_count=1,
                    last_called_at=datetime.utcnow()
                )
                db.session.add(stat)
            
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # 记录错误但不影响主流程
            import traceback
            print(f"[API统计] 记录API调用失败: {e}", file=sys.stderr)
            traceback.print_exc()
    
    @staticmethod
    def get_stats_by_endpoint(start_date: Optional[datetime] = None, 
                              end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        按端点查询统计
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            统计列表，每个元素包含端点的汇总统计
        """
        try:
            query = db.session.query(
                ApiCallStat.endpoint,
                ApiCallStat.method,
                func.sum(ApiCallStat.call_count).label('total_calls'),
                func.max(ApiCallStat.last_called_at).label('last_called'),
                func.count(func.distinct(ApiCallStat.user_id)).label('unique_users')
            ).group_by(ApiCallStat.endpoint, ApiCallStat.method)
            
            if start_date:
                query = query.filter(ApiCallStat.created_at >= start_date)
            if end_date:
                query = query.filter(ApiCallStat.created_at <= end_date)
            
            results = query.all()
            
            stats = []
            for result in results:
                stats.append({
                    'endpoint': result.endpoint,
                    'method': result.method,
                    'total_calls': result.total_calls or 0,
                    'last_called': result.last_called.isoformat() if result.last_called else None,
                    'last_called_at': result.last_called.isoformat() if result.last_called else None,  # 前端使用last_called_at
                    'unique_users': result.unique_users or 0,
                    'user_count': result.unique_users or 0  # 前端使用user_count
                })
            
            return stats
        except Exception as e:
            print(f"[API统计] 查询端点统计失败: {e}", file=sys.stderr)
            return []
    
    @staticmethod
    def get_stats_by_user(user_id: int, start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        按用户查询统计（为未来扩展预留）
        
        Args:
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            该用户的API调用统计列表
        """
        try:
            query = ApiCallStat.query.filter_by(user_id=user_id)
            
            if start_date:
                query = query.filter(ApiCallStat.created_at >= start_date)
            if end_date:
                query = query.filter(ApiCallStat.created_at <= end_date)
            
            stats = query.all()
            return [stat.to_dict() for stat in stats]
        except Exception as e:
            print(f"[API统计] 查询用户统计失败: {e}", file=sys.stderr)
            return []
    
    @staticmethod
    def get_top_endpoints(limit: int = 10, start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        获取调用最多的端点（Top N）
        
        Args:
            limit: 返回数量限制
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Top N端点统计列表
        """
        try:
            query = db.session.query(
                ApiCallStat.endpoint,
                ApiCallStat.method,
                func.sum(ApiCallStat.call_count).label('total_calls'),
                func.max(ApiCallStat.last_called_at).label('last_called'),
                func.count(func.distinct(ApiCallStat.user_id)).label('unique_users')
            ).group_by(ApiCallStat.endpoint, ApiCallStat.method)
            
            if start_date:
                query = query.filter(ApiCallStat.created_at >= start_date)
            if end_date:
                query = query.filter(ApiCallStat.created_at <= end_date)
            
            results = query.order_by(func.sum(ApiCallStat.call_count).desc()).limit(limit).all()
            
            stats = []
            for result in results:
                stats.append({
                    'endpoint': result.endpoint,
                    'method': result.method,
                    'total_calls': result.total_calls or 0,
                    'last_called': result.last_called.isoformat() if result.last_called else None,
                    'last_called_at': result.last_called.isoformat() if result.last_called else None,  # 前端使用last_called_at
                    'unique_users': result.unique_users or 0,
                    'user_count': result.unique_users or 0  # 前端使用user_count
                })
            
            return stats
        except Exception as e:
            print(f"[API统计] 查询Top端点失败: {e}", file=sys.stderr)
            return []
    
    @staticmethod
    def get_endpoint_detail(endpoint: str, start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        获取端点详细统计（包括用户分布）
        
        Args:
            endpoint: API端点路径
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            端点详细统计信息
        """
        try:
            query = ApiCallStat.query.filter_by(endpoint=endpoint)
            
            if start_date:
                query = query.filter(ApiCallStat.created_at >= start_date)
            if end_date:
                query = query.filter(ApiCallStat.created_at <= end_date)
            
            stats = query.all()
            
            # 汇总统计
            total_calls = sum(stat.call_count for stat in stats)
            methods = {}
            status_codes = {}
            users = {}
            
            for stat in stats:
                # 按方法统计
                method_key = stat.method
                if method_key not in methods:
                    methods[method_key] = 0
                methods[method_key] += stat.call_count
                
                # 按状态码统计
                status_key = stat.status_code
                if status_key not in status_codes:
                    status_codes[status_key] = 0
                status_codes[status_key] += stat.call_count
                
                # 按用户统计
                if stat.user_id:
                    user_key = stat.username or f"User_{stat.user_id}"
                    if user_key not in users:
                        users[user_key] = 0
                    users[user_key] += stat.call_count
            
            # 获取最后调用时间
            last_called = max((stat.last_called_at for stat in stats), default=None)
            
            return {
                'endpoint': endpoint,
                'total_calls': total_calls,
                'last_called': last_called.isoformat() if last_called else None,
                'methods': methods,
                'status_codes': status_codes,
                'users': users,
                'unique_users': len(users)
            }
        except Exception as e:
            print(f"[API统计] 查询端点详情失败: {e}", file=sys.stderr)
            return {
                'endpoint': endpoint,
                'total_calls': 0,
                'last_called': None,
                'methods': {},
                'status_codes': {},
                'users': {},
                'unique_users': 0
            }
    
    @staticmethod
    def get_summary(start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        获取统计摘要
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            统计摘要信息
        """
        try:
            # 总调用次数
            total_calls_query = db.session.query(func.sum(ApiCallStat.call_count))
            if start_date:
                total_calls_query = total_calls_query.filter(ApiCallStat.created_at >= start_date)
            if end_date:
                total_calls_query = total_calls_query.filter(ApiCallStat.created_at <= end_date)
            total_calls = total_calls_query.scalar() or 0
            
            # 唯一端点数量
            unique_endpoints_query = db.session.query(func.count(func.distinct(ApiCallStat.endpoint)))
            if start_date:
                unique_endpoints_query = unique_endpoints_query.filter(ApiCallStat.created_at >= start_date)
            if end_date:
                unique_endpoints_query = unique_endpoints_query.filter(ApiCallStat.created_at <= end_date)
            unique_endpoints = unique_endpoints_query.scalar() or 0
            
            # 活跃用户数（有API调用的用户）
            active_users_query = db.session.query(func.count(func.distinct(ApiCallStat.user_id))).filter(
                ApiCallStat.user_id.isnot(None)
            )
            if start_date:
                active_users_query = active_users_query.filter(ApiCallStat.created_at >= start_date)
            if end_date:
                active_users_query = active_users_query.filter(ApiCallStat.created_at <= end_date)
            active_users = active_users_query.scalar() or 0
            
            return {
                'total_calls': total_calls,
                'total_endpoints': unique_endpoints,  # 前端使用total_endpoints
                'unique_endpoints': unique_endpoints,  # 保持向后兼容
                'total_active_users': active_users,  # 前端使用total_active_users
                'active_users': active_users  # 保持向后兼容
            }
        except Exception as e:
            print(f"[API统计] 查询统计摘要失败: {e}", file=sys.stderr)
            return {
                'total_calls': 0,
                'total_endpoints': 0,
                'unique_endpoints': 0,
                'total_active_users': 0,
                'active_users': 0
            }

