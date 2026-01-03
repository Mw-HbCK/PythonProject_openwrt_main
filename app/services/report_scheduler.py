#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报表调度器
使用 schedule 库实现定时报表生成任务
"""
import os
import sys
import threading
import time
import schedule
from datetime import datetime, timedelta
from typing import Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.services.report_service import ReportService
from app.services.config_manager import load_config_file, get_config_file_path
from app.models.report_models import ReportHistory, db
from app.models.user_models import db as user_db


class ReportScheduler:
    """报表调度器类"""
    
    def __init__(self, app):
        """
        初始化报表调度器
        
        Args:
            app: Flask应用实例
        """
        self.app = app
        self.report_service = ReportService(app)
        self.scheduler_thread = None
        self.is_running = False
        self.stop_event = threading.Event()
    
    def _load_report_config(self):
        """
        加载报表配置
        
        Returns:
            dict: 报表配置
        """
        try:
            config_file = get_config_file_path()
            # 扩展load_config_file以支持report_config
            try:
                _, _, _, _, _, report_config, _ = load_config_file(config_file)
            except:
                # 如果load_config_file不支持report_config，返回空配置
                report_config = {}
            return report_config
        except Exception as e:
            print(f"[报表调度器] 加载配置失败: {e}", file=sys.stderr)
            return {}
    
    def _run_report_job(self, report_type: str):
        """
        执行报表生成任务
        这个方法在调度器线程中运行
        
        Args:
            report_type: 报表类型（daily/weekly/monthly）
        """
        try:
            with self.app.app_context():
                print(f"[报表调度器] 开始执行{report_type}报表生成任务...")
                
                # 加载配置
                report_config = self._load_report_config()
                report_enabled = report_config.get('report_enabled', 'false').lower() == 'true'
                
                if not report_enabled:
                    print(f"[报表调度器] 报表生成未启用，跳过")
                    return
                
                # 检查对应类型的报表是否启用
                type_enabled_key = f'{report_type}_enabled'
                if report_config.get(type_enabled_key, 'true').lower() == 'false':
                    print(f"[报表调度器] {report_type}报表未启用，跳过")
                    return
                
                # 计算报表周期
                now = datetime.utcnow()
                period_start = None
                period_end = None
                
                if report_type == 'daily':
                    # 日报：生成前一天的报表
                    period_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                    period_end = period_start + timedelta(days=1) - timedelta(seconds=1)
                elif report_type == 'weekly':
                    # 周报：生成上一周的报表
                    days_since_monday = now.weekday()
                    last_week_start = (now - timedelta(days=days_since_monday + 7)).replace(hour=0, minute=0, second=0, microsecond=0)
                    period_start = last_week_start
                    period_end = last_week_start + timedelta(days=7) - timedelta(seconds=1)
                elif report_type == 'monthly':
                    # 月报：生成上一个月的报表
                    if now.month == 1:
                        period_start = now.replace(year=now.year-1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)
                    else:
                        period_start = now.replace(month=now.month-1, day=1, hour=0, minute=0, second=0, microsecond=0)
                    # 计算上个月的最后一天
                    if period_start.month == 12:
                        period_end = period_start.replace(year=period_start.year+1, month=1, day=1) - timedelta(seconds=1)
                    else:
                        period_end = period_start.replace(month=period_start.month+1, day=1) - timedelta(seconds=1)
                
                # 生成报表周期字符串
                period_str = period_start.strftime('%Y%m%d')
                if report_type == 'weekly':
                    period_str = period_start.strftime('%Y%m%d')
                elif report_type == 'monthly':
                    period_str = period_start.strftime('%Y%m')
                
                # 检查是否已经生成过该周期的报表
                existing_report = ReportHistory.query.filter_by(
                    report_type=report_type,
                    report_period=period_str,
                    status='success'
                ).first()
                
                if existing_report:
                    print(f"[报表调度器] {report_type}报表（周期: {period_str}）已存在，跳过")
                    return
                
                # 执行报表生成
                try:
                    file_paths, total_size = self.report_service.generate_report(
                        report_type=report_type,
                        period_start=period_start,
                        period_end=period_end,
                        report_config=report_config
                    )
                    
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
                    
                    print(f"[报表调度器] {report_type}报表生成成功: 周期={period_str}, 大小={total_size} 字节")
                    
                    # 如果启用邮件发送，发送报表
                    email_enabled = report_config.get('email_enabled', 'false').lower() == 'true'
                    if email_enabled:
                        try:
                            self._send_report_email(report_record, report_config)
                        except Exception as e:
                            print(f"[报表调度器] 发送报表邮件失败: {e}", file=sys.stderr)
                    
                    # 清理旧报表
                    try:
                        keep_count_str = report_config.get('keep_count', '30')
                        # 去除注释（如果有）
                        if '#' in keep_count_str:
                            keep_count_str = keep_count_str.split('#')[0]
                        keep_count = int(keep_count_str.strip())
                        self._delete_old_reports(keep_count)
                    except Exception as e:
                        print(f"[报表调度器] 清理旧报表失败: {e}", file=sys.stderr)
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"[报表调度器] 报表生成失败: {error_msg}", file=sys.stderr)
                    
                    # 记录失败的报表历史
                    try:
                        report_record = ReportHistory(
                            report_type=report_type,
                            report_period=period_str,
                            file_path_pdf=None,
                            file_path_html=None,
                            file_path_excel=None,
                            file_size=0,
                            status='failed',
                            error_message=error_msg
                        )
                        user_db.session.add(report_record)
                        user_db.session.commit()
                    except Exception as db_error:
                        print(f"[报表调度器] 保存报表历史失败: {db_error}", file=sys.stderr)
                        
        except Exception as e:
            print(f"[报表调度器] 执行报表任务时发生异常: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    def _send_report_email(self, report_record: ReportHistory, report_config: dict):
        """
        发送报表邮件
        
        Args:
            report_record: 报表记录
            report_config: 报表配置
        """
        try:
            from app.services.notification_service import NotificationService
            
            email_recipients = report_config.get('email_recipients', '')
            if not email_recipients:
                print("[报表调度器] 邮件收件人未配置", file=sys.stderr)
                return
            
            recipients = [email.strip() for email in email_recipients.split(',') if email.strip()]
            if not recipients:
                print("[报表调度器] 邮件收件人列表为空", file=sys.stderr)
                return
            
            notification_service = NotificationService()
            
            # 报表类型名称
            report_type_names = {'daily': '日报', 'weekly': '周报', 'monthly': '月报'}
            report_type_name = report_type_names.get(report_record.report_type, '报表')
            
            # 邮件主题
            subject = f"流量监控{report_type_name} - {report_record.report_period}"
            
            # 邮件正文
            body = f"""
            <h2>流量监控{report_type_name}</h2>
            <p>报表周期: {report_record.report_period}</p>
            <p>生成时间: {report_record.created_at.strftime('%Y-%m-%d %H:%M:%S') if report_record.created_at else '未知'}</p>
            <p>文件大小: {report_record._format_size(report_record.file_size)}</p>
            <p>请查看附件获取详细报表。</p>
            """
            
            # 准备附件
            attachments = []
            if report_record.file_path_pdf and os.path.exists(report_record.file_path_pdf):
                attachments.append({
                    'filename': os.path.basename(report_record.file_path_pdf),
                    'path': report_record.file_path_pdf
                })
            
            # 发送邮件
            notification_service.send_email(
                to=recipients,
                subject=subject,
                body=body,
                attachments=attachments
            )
            
            # 更新报表记录的发送时间
            report_record.sent_at = datetime.utcnow()
            user_db.session.commit()
            
            print(f"[报表调度器] 报表邮件已发送: {recipients}")
            
        except Exception as e:
            print(f"[报表调度器] 发送报表邮件失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    def _delete_old_reports(self, keep_count: int):
        """
        删除旧的报表文件，保留最近N个
        
        Args:
            keep_count: 保留的报表数量
        """
        try:
            # 获取所有成功的报表，按创建时间倒序
            reports = ReportHistory.query.filter_by(status='success')\
                .order_by(ReportHistory.created_at.desc()).all()
            
            if len(reports) <= keep_count:
                return
            
            # 需要删除的报表（保留最新的keep_count个）
            to_delete = reports[keep_count:]
            deleted_count = 0
            
            for report in to_delete:
                try:
                    # 删除文件
                    import shutil
                    files_to_delete = []
                    if report.file_path_pdf and os.path.exists(report.file_path_pdf):
                        files_to_delete.append(report.file_path_pdf)
                    if report.file_path_html and os.path.exists(report.file_path_html):
                        files_to_delete.append(report.file_path_html)
                    if report.file_path_excel and os.path.exists(report.file_path_excel):
                        files_to_delete.append(report.file_path_excel)
                    
                    for file_path in files_to_delete:
                        try:
                            os.remove(file_path)
                        except Exception as e:
                            print(f"[报表调度器] 删除文件失败 {file_path}: {e}", file=sys.stderr)
                    
                    # 删除数据库记录
                    user_db.session.delete(report)
                    deleted_count += 1
                except Exception as e:
                    print(f"[报表调度器] 删除报表失败 {report.id}: {e}", file=sys.stderr)
            
            if deleted_count > 0:
                user_db.session.commit()
                print(f"[报表调度器] 已清理 {deleted_count} 个旧报表")
            
        except Exception as e:
            print(f"[报表调度器] 清理旧报表失败: {e}", file=sys.stderr)
            user_db.session.rollback()
    
    def _schedule_reports(self):
        """
        根据配置调度报表任务
        """
        try:
            report_config = self._load_report_config()
            report_enabled = report_config.get('report_enabled', 'false').lower() == 'true'
            
            if not report_enabled:
                return
            
            # 清除所有现有任务
            schedule.clear()
            
            # 调度日报
            if report_config.get('daily_enabled', 'true').lower() == 'true':
                daily_time_str = report_config.get('daily_time', '02:00')
                # 去除注释（如果有）
                if '#' in daily_time_str:
                    daily_time_str = daily_time_str.split('#')[0]
                daily_time = daily_time_str.strip()
                schedule.every().day.at(daily_time).do(self._run_report_job, 'daily')
                print(f"[报表调度器] 已调度日报任务: {daily_time}")
            
            # 调度周报
            if report_config.get('weekly_enabled', 'true').lower() == 'true':
                weekly_time_str = report_config.get('weekly_time', '02:00')
                # 去除注释（如果有）
                if '#' in weekly_time_str:
                    weekly_time_str = weekly_time_str.split('#')[0]
                weekly_time = weekly_time_str.strip()
                weekly_day_str = report_config.get('weekly_day', 'monday').lower()
                # 每周一执行
                if weekly_day_str == 'monday':
                    schedule.every().monday.at(weekly_time).do(self._run_report_job, 'weekly')
                elif weekly_day_str == 'tuesday':
                    schedule.every().tuesday.at(weekly_time).do(self._run_report_job, 'weekly')
                elif weekly_day_str == 'wednesday':
                    schedule.every().wednesday.at(weekly_time).do(self._run_report_job, 'weekly')
                elif weekly_day_str == 'thursday':
                    schedule.every().thursday.at(weekly_time).do(self._run_report_job, 'weekly')
                elif weekly_day_str == 'friday':
                    schedule.every().friday.at(weekly_time).do(self._run_report_job, 'weekly')
                elif weekly_day_str == 'saturday':
                    schedule.every().saturday.at(weekly_time).do(self._run_report_job, 'weekly')
                elif weekly_day_str == 'sunday':
                    schedule.every().sunday.at(weekly_time).do(self._run_report_job, 'weekly')
                else:
                    schedule.every().monday.at(weekly_time).do(self._run_report_job, 'weekly')
                print(f"[报表调度器] 已调度周报任务: {weekly_day_str}, {weekly_time}")
            
            # 调度月报
            if report_config.get('monthly_enabled', 'true').lower() == 'true':
                monthly_time_str = report_config.get('monthly_time', '02:00')
                # 去除注释（如果有）
                if '#' in monthly_time_str:
                    monthly_time_str = monthly_time_str.split('#')[0]
                monthly_time = monthly_time_str.strip()
                monthly_day_str = report_config.get('monthly_day', '1')
                # 去除注释（如果有）
                if '#' in monthly_day_str:
                    monthly_day_str = monthly_day_str.split('#')[0]
                monthly_day = int(monthly_day_str.strip())
                
                # schedule库不支持每月执行，使用每日检查，在实际执行时判断日期
                def check_and_run_monthly():
                    now = datetime.utcnow()
                    if now.day == monthly_day:
                        self._run_report_job('monthly')
                
                schedule.every().day.at(monthly_time).do(check_and_run_monthly)
                print(f"[报表调度器] 已调度月报任务: 每月{monthly_day}号, {monthly_time}")
            
        except Exception as e:
            print(f"[报表调度器] 调度报表任务失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    def _scheduler_loop(self):
        """
        调度器循环（在后台线程中运行）
        """
        print("[报表调度器] 调度器线程已启动")
        
        # 初始调度
        with self.app.app_context():
            self._schedule_reports()
        
        # 运行调度循环
        while not self.stop_event.is_set():
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                print(f"[报表调度器] 调度循环错误: {e}", file=sys.stderr)
                time.sleep(60)
        
        print("[报表调度器] 调度器线程已停止")
    
    def start(self):
        """启动报表调度器"""
        if self.is_running:
            print("[报表调度器] 调度器已在运行", file=sys.stderr)
            return
        
        try:
            with self.app.app_context():
                report_config = self._load_report_config()
                report_enabled = report_config.get('report_enabled', 'false').lower() == 'true'
                
                if not report_enabled:
                    print("[报表调度器] 报表生成未启用，不启动调度器")
                    return
            
            self.is_running = True
            self.stop_event.clear()
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            print("[报表调度器] 报表调度器已启动")
            
        except Exception as e:
            print(f"[报表调度器] 启动失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            self.is_running = False
    
    def stop(self):
        """停止报表调度器"""
        if not self.is_running:
            return
        
        print("[报表调度器] 正在停止报表调度器...")
        self.is_running = False
        self.stop_event.set()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        schedule.clear()
        print("[报表调度器] 报表调度器已停止")
    
    def reload_config(self):
        """重新加载配置并重新调度"""
        if self.is_running:
            with self.app.app_context():
                self._schedule_reports()


# 全局调度器实例
_report_scheduler: Optional[ReportScheduler] = None


def get_report_scheduler(app=None):
    """
    获取报表调度器实例（单例模式）
    
    Args:
        app: Flask应用实例
    
    Returns:
        ReportScheduler: 报表调度器实例
    """
    global _report_scheduler
    if _report_scheduler is None and app:
        _report_scheduler = ReportScheduler(app)
    return _report_scheduler


def start_report_scheduler(app):
    """
    启动报表调度器
    
    Args:
        app: Flask应用实例
    """
    scheduler = get_report_scheduler(app)
    if scheduler:
        scheduler.start()


def stop_report_scheduler():
    """停止报表调度器"""
    global _report_scheduler
    if _report_scheduler:
        _report_scheduler.stop()
        _report_scheduler = None

