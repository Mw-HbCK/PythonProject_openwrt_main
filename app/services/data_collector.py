#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据收集服务
定时请求API并将数据存储到数据库
"""
import requests
import time
import threading
import sys
from datetime import datetime
from flask import Flask
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.models.database_models import db, Device, TotalTraffic, DeviceTraffic, init_database_tables
from app.utils.logger import get_logger
from app.services.database_config_service import get_database_uri, get_traffic_database_uri

# 创建Flask应用（仅用于数据库操作）
app = Flask(__name__)

# 配置数据库（MySQL）
try:
    database_uri, _ = get_database_uri()
    app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
except Exception as e:
    print(f"警告: 读取数据库配置失败: {e}，使用默认配置", file=sys.stderr)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost:3306/bandix_monitor?charset=utf8mb4'

try:
    traffic_uri, traffic_bind_key = get_traffic_database_uri()
    app.config['SQLALCHEMY_BINDS'] = {
        traffic_bind_key: traffic_uri
    }
except Exception as e:
    print(f"警告: 读取流量数据库配置失败: {e}，使用默认配置", file=sys.stderr)
    app.config['SQLALCHEMY_BINDS'] = {
        'traffic': 'mysql+pymysql://root:password@localhost:3306/bandix_monitor?charset=utf8mb4'
    }

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)
init_database_tables(app, bind_key='traffic')

# 配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000")
API_TOKEN = os.getenv("API_TOKEN", "")  # 优先使用环境变量
COLLECT_INTERVAL = float(os.getenv("COLLECT_INTERVAL", "1.0"))  # 秒
IS_RUNNING = False
COLLECTOR_THREAD = None

# 获取日志记录器
logger = get_logger('data_collector', category='business')
error_logger = get_logger('data_collector', category='error')


def load_collect_interval_from_config():
    """
    从配置文件读取数据收集间隔
    """
    global COLLECT_INTERVAL
    
    # 如果环境变量已设置，优先使用环境变量
    if os.getenv("COLLECT_INTERVAL"):
        COLLECT_INTERVAL = float(os.getenv("COLLECT_INTERVAL"))
        return COLLECT_INTERVAL
    
    try:
        import configparser
        # 配置文件路径：项目根目录/app/config/bandix_config.ini
        config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config", "bandix_config.ini")
        
        if os.path.exists(config_file):
            config = configparser.ConfigParser()
            config.read(config_file, encoding='utf-8')
            if "collector" in config and config["collector"].get("collect_interval"):
                COLLECT_INTERVAL = float(config["collector"].get("collect_interval"))
                return COLLECT_INTERVAL
        else:
            # 尝试相对路径（如果工作目录是项目根目录）
            config_file_relative = os.path.join("app", "config", "bandix_config.ini")
            if os.path.exists(config_file_relative):
                config = configparser.ConfigParser()
                config.read(config_file_relative, encoding='utf-8')
                if "collector" in config and config["collector"].get("collect_interval"):
                    COLLECT_INTERVAL = float(config["collector"].get("collect_interval"))
                    return COLLECT_INTERVAL
    except Exception as e:
        if error_logger:
            error_logger.error(f"读取收集间隔配置失败: {e}，使用默认值1.0秒")
        else:
            print(f"[数据收集服务] 读取收集间隔配置失败: {e}，使用默认值1.0秒", file=sys.stderr)
    
    return COLLECT_INTERVAL


def reload_collector_config():
    """
    重新加载数据收集服务配置
    """
    global COLLECT_INTERVAL
    load_collect_interval_from_config()
    if logger:
        logger.info(f"配置已重新加载，收集间隔: {COLLECT_INTERVAL}秒")
    else:
        print(f"[数据收集服务] 配置已重新加载，收集间隔: {COLLECT_INTERVAL}秒")


def load_api_token_from_config():
    """
    从配置文件读取API密钥
    """
    global API_TOKEN
    
    # 如果环境变量已设置，优先使用环境变量
    if API_TOKEN:
        return API_TOKEN
    
    try:
        import configparser
        # 配置文件路径：项目根目录/app/config/bandix_config.ini
        config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config", "bandix_config.ini")
        
        if os.path.exists(config_file):
            config = configparser.ConfigParser()
            config.read(config_file, encoding='utf-8')
            if "api" in config and config["api"].get("api_key"):
                API_TOKEN = config["api"].get("api_key").strip()
                return API_TOKEN
        else:
            # 尝试相对路径（如果工作目录是项目根目录）
            config_file_relative = os.path.join("app", "config", "bandix_config.ini")
            if os.path.exists(config_file_relative):
                config = configparser.ConfigParser()
                config.read(config_file_relative, encoding='utf-8')
                if "api" in config and config["api"].get("api_key"):
                    API_TOKEN = config["api"].get("api_key").strip()
                    return API_TOKEN
    except Exception as e:
        if error_logger:
            error_logger.error(f"读取配置文件失败: {e}")
        else:
            print(f"[数据收集服务] 读取配置文件失败: {e}", file=sys.stderr)
    
    return None


# 初始化时尝试从配置文件读取API密钥和收集间隔
load_api_token_from_config()
load_collect_interval_from_config()


def save_traffic_data(data):
    """
    保存流量数据到数据库
    """
    with app.app_context():
        try:
            # 获取或创建当前时间戳
            current_time = datetime.utcnow()
            
            # 1. 保存全网流量数据
            if data.get("total"):
                total_data = data["total"]
                timestamp_ms = total_data.get("timestamp")
                
                total_traffic = TotalTraffic(
                    timestamp=current_time,
                    timestamp_ms=timestamp_ms,
                    down_speed_bytes=total_data["down_speed"]["bytes_per_second"],
                    up_speed_bytes=total_data["up_speed"]["bytes_per_second"],
                    total_download_bytes=total_data["total_download"]["bytes"],
                    total_upload_bytes=total_data["total_upload"]["bytes"],
                    down_speed_formatted=total_data["down_speed"]["formatted"],
                    up_speed_formatted=total_data["up_speed"]["formatted"],
                    total_download_formatted=total_data["total_download"]["formatted"],
                    total_upload_formatted=total_data["total_upload"]["formatted"]
                )
                db.session.add(total_traffic)
            
            # 2. 保存设备信息和设备流量数据
            if data.get("devices"):
                for device_data in data["devices"]:
                    mac = device_data.get("mac")
                    if not mac:
                        continue
                    
                    # 获取或创建设备记录
                    device = Device.query.filter_by(mac=mac).first()
                    if not device:
                        device = Device(
                            mac=mac,
                            hostname=device_data.get("hostname", "未知"),
                            ip=device_data.get("ip", "-")
                        )
                        db.session.add(device)
                        db.session.flush()  # 获取device.id
                    else:
                        # 更新设备信息
                        device.hostname = device_data.get("hostname", device.hostname)
                        device.ip = device_data.get("ip", device.ip)
                        device.updated_at = current_time
                    
                    # 保存设备流量数据
                    timestamp_ms = device_data.get("timestamp")
                    device_traffic = DeviceTraffic(
                        device_id=device.id,
                        timestamp=current_time,
                        timestamp_ms=timestamp_ms,
                        down_speed_bytes=device_data["down_speed"]["bytes_per_second"],
                        up_speed_bytes=device_data["up_speed"]["bytes_per_second"],
                        total_download_bytes=device_data["total_download"]["bytes"],
                        total_upload_bytes=device_data["total_upload"]["bytes"],
                        down_speed_formatted=device_data["down_speed"]["formatted"],
                        up_speed_formatted=device_data["up_speed"]["formatted"],
                        total_download_formatted=device_data["total_download"]["formatted"],
                        total_upload_formatted=device_data["total_upload"]["formatted"]
                    )
                    db.session.add(device_traffic)
            
            db.session.commit()
            
            # 数据保存成功后，触发告警检查
            try:
                from app.services.alert_checker import check_alerts
                check_alerts(app)
            except Exception as e:
                # 告警检查失败不应该影响数据收集
                if error_logger:
                    error_logger.error(f"告警检查失败: {e}", exc_info=True)
                else:
                    print(f"[数据收集服务] 告警检查失败: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            if error_logger:
                error_logger.error(f"保存数据失败: {e}", exc_info=True)
            else:
                print(f"保存数据失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return False


def collect_data_once():
    """
    收集一次数据
    """
    try:
        # 每次收集时重新读取配置（以防配置被修改）
        api_token = API_TOKEN or load_api_token_from_config()
        
        headers = {}
        if api_token:
            headers["X-API-Key"] = api_token
        
        response = requests.get(
            f"{API_BASE_URL}/api/monitor",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success") and result.get("data"):
                if save_traffic_data(result["data"]):
                    if logger:
                        logger.debug("数据收集成功")
                    else:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 数据收集成功")
                else:
                    if error_logger:
                        error_logger.error("数据保存失败")
                    else:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 数据保存失败", file=sys.stderr)
            else:
                error_msg = result.get("error", "未知错误")
                if error_logger:
                    error_logger.warning(f"API返回错误: {error_msg}")
                else:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] API返回错误: {error_msg}", file=sys.stderr)
        elif response.status_code == 503:
            # 503 Service Unavailable - 设备不可用或登录失败，这是可预期的错误
            # 不打印错误信息，避免控制台刷屏（只在debug模式下打印）
            try:
                result = response.json()
                error_msg = result.get("error", "设备不可用")
            except:
                error_msg = "设备不可用"
            # 只在debug模式下打印
            if os.getenv("DEBUG", "").lower() == "true":
                if error_logger:
                    error_logger.debug(f"设备不可用: {error_msg}")
                else:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 设备不可用: {error_msg}", file=sys.stderr)
        else:
            if error_logger:
                error_logger.warning(f"API请求失败: HTTP {response.status_code}")
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] API请求失败: HTTP {response.status_code}", file=sys.stderr)
            
    except requests.exceptions.RequestException as e:
        if error_logger:
            error_logger.error(f"网络错误: {e}", exc_info=True)
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 网络错误: {e}", file=sys.stderr)
    except Exception as e:
        if error_logger:
            error_logger.error(f"收集数据时发生错误: {e}", exc_info=True)
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 收集数据时发生错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


def collector_loop():
    """
    数据收集循环
    """
    global IS_RUNNING, COLLECT_INTERVAL
    IS_RUNNING = True
    
    # 确保API密钥已加载
    api_token = API_TOKEN or load_api_token_from_config()
    
    # 确保收集间隔已加载
    load_collect_interval_from_config()
    
    if logger:
        logger.info(f"数据收集服务已启动，每 {COLLECT_INTERVAL} 秒收集一次数据")
        logger.info(f"API地址: {API_BASE_URL}")
        logger.info(f"API密钥: {'已配置' if api_token else '未配置（可能导致认证失败）'}")
        logger.info(f"数据库: traffic_data.db")
    else:
        print(f"数据收集服务已启动，每 {COLLECT_INTERVAL} 秒收集一次数据")
        print(f"API地址: {API_BASE_URL}")
        print(f"API密钥: {'已配置' if api_token else '未配置（可能导致认证失败）'}")
        print(f"数据库: traffic_data.db")
    
    while IS_RUNNING:
        try:
            # 每次循环前重新加载配置（支持动态更新）
            current_interval = load_collect_interval_from_config()
            collect_data_once()
            time.sleep(current_interval)
        except KeyboardInterrupt:
            break
        except Exception as e:
            if error_logger:
                error_logger.error(f"收集循环错误: {e}", exc_info=True)
            else:
                print(f"收集循环错误: {e}", file=sys.stderr)
            time.sleep(COLLECT_INTERVAL)
    
    if logger:
        logger.info("数据收集服务已停止")
    else:
        print("数据收集服务已停止")


def start_collector():
    """
    启动数据收集服务（在独立线程中运行）
    """
    global COLLECTOR_THREAD, IS_RUNNING
    
    if IS_RUNNING:
        if error_logger:
            error_logger.warning("数据收集服务已在运行")
        else:
            print("数据收集服务已在运行", file=sys.stderr)
        return False
    
    # 重置运行状态（防止之前的状态影响）
    IS_RUNNING = False
    
    COLLECTOR_THREAD = threading.Thread(target=collector_loop, daemon=True)
    COLLECTOR_THREAD.start()
    return True


def stop_collector():
    """
    停止数据收集服务
    """
    global IS_RUNNING
    
    if not IS_RUNNING:
        return False
    
    IS_RUNNING = False
    if COLLECTOR_THREAD:
        COLLECTOR_THREAD.join(timeout=5)
    return True


if __name__ == "__main__":
    # 直接运行此文件时，启动数据收集服务
    print("=" * 60)
    print("Bandix Monitor 数据收集服务")
    print("=" * 60)
    
    if not API_TOKEN:
        print("警告: 未设置 API_TOKEN 环境变量，可能无法访问需要认证的API", file=sys.stderr)
        print("设置方式: export API_TOKEN=your-token", file=sys.stderr)
    
    try:
        collector_loop()
    except KeyboardInterrupt:
        if logger:
            logger.info("\n正在停止数据收集服务...")
        else:
            print("\n正在停止数据收集服务...")
        stop_collector()
        if logger:
            logger.info("数据收集服务已停止")
        else:
            print("数据收集服务已停止")

