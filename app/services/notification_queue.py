#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单通知任务队列
使用线程池处理异步通知任务
"""
import queue
import threading
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.services.notification_service import NotificationService
from app.models.alert_models import AlertHistory
from app.models.user_models import db


# 全局任务队列
_task_queue = queue.Queue()
_worker_threads = []
_is_running = False
_max_workers = 4


def _worker_thread(app):
    """
    工作线程，从队列中取出任务并执行
    
    Args:
        app: Flask 应用实例（用于应用上下文）
    """
    global _task_queue, _is_running
    
    while _is_running:
        try:
            # 从队列中获取任务（超时1秒，以便检查 _is_running 状态）
            try:
                task = _task_queue.get(timeout=1)
            except queue.Empty:
                continue
            
            try:
                alert_history_id, notification_methods = task
                
                # 在 Flask 应用上下文中执行
                with app.app_context():
                    # 获取告警历史记录
                    alert_history = AlertHistory.query.get(alert_history_id)
                    if not alert_history:
                        print(f"[通知队列] 告警历史记录 {alert_history_id} 不存在", file=sys.stderr)
                        _task_queue.task_done()
                        continue
                    
                    # 获取通知服务实例
                    notification_service = NotificationService()
                    
                    # 转换为字典格式
                    alert_dict = alert_history.to_dict()
                    
                    # 发送通知
                    results = notification_service.send_notification(
                        notification_methods=notification_methods,
                        alert_history=alert_dict
                    )
                    
                    # 汇总结果
                    success_count = sum(1 for success, _ in results.values() if success)
                    total_count = len(results)
                    
                    print(f"[通知队列] 告警 {alert_history_id} 通知发送完成: {success_count}/{total_count} 成功")
                    
            except Exception as e:
                error_msg = str(e)
                print(f"[通知队列] 发送通知任务失败: {error_msg}", file=sys.stderr)
                import traceback
                traceback.print_exc()
            finally:
                _task_queue.task_done()
                
        except Exception as e:
            print(f"[通知队列] 工作线程错误: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()


def start_workers(app, num_workers=None):
    """
    启动工作线程
    
    Args:
        app: Flask 应用实例
        num_workers: 工作线程数量（默认使用全局 _max_workers）
    """
    global _worker_threads, _is_running, _max_workers
    
    if _is_running:
        print("[通知队列] 工作线程已在运行", file=sys.stderr)
        return
    
    _is_running = True
    
    if num_workers is None:
        num_workers = _max_workers
    
    # 启动工作线程
    for i in range(num_workers):
        thread = threading.Thread(
            target=_worker_thread,
            args=(app,),
            daemon=True,
            name=f"NotificationWorker-{i+1}"
        )
        thread.start()
        _worker_threads.append(thread)
    
    print(f"[通知队列] 已启动 {num_workers} 个工作线程")


def stop_workers():
    """停止工作线程"""
    global _worker_threads, _is_running
    
    if not _is_running:
        return
    
    _is_running = False
    
    # 等待所有任务完成
    _task_queue.join()
    
    # 等待所有工作线程结束
    for thread in _worker_threads:
        thread.join(timeout=5)
    
    _worker_threads.clear()
    print("[通知队列] 工作线程已停止")


def send_notification_async(alert_history_id: int, notification_methods: list):
    """
    异步发送通知（将任务加入队列）
    
    Args:
        alert_history_id: 告警历史记录ID
        notification_methods: 通知方式列表，如 ['page', 'email', 'webhook']
    """
    global _task_queue, _is_running
    
    if not _is_running:
        print("[通知队列] 警告: 工作线程未启动，通知任务将不会被执行", file=sys.stderr)
        return
    
    try:
        _task_queue.put((alert_history_id, notification_methods), block=False)
    except queue.Full:
        print(f"[通知队列] 警告: 任务队列已满，通知任务 {alert_history_id} 将被丢弃", file=sys.stderr)

