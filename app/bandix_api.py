#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenWrt Bandix 流量监控 API 服务
提供 HTTP API 接口来获取监控数据
"""
from flask import Flask, jsonify, request, render_template
from functools import wraps
from flasgger import Swagger
import os
import sys

# 添加项目根目录到路径，以便导入模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入服务模块（从app目录的相对导入）
from app.services.bandix_monitor import BandixMonitor
from app.models.user_models import db, User, init_db as init_user_db
from app.api.user_api import user_bp
from app.api.database_api import db_bp
from app.api.alert_api import alert_bp
from app.api.config_api import config_bp
from app.models.database_models import Device, TotalTraffic, DeviceTraffic, init_database_tables
from app.services.data_collector import start_collector

app = Flask(__name__, template_folder='templates')

# 配置用户数据库
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)  # 用于session加密

# 配置流量数据库（使用BINDS）
if 'SQLALCHEMY_BINDS' not in app.config:
    app.config['SQLALCHEMY_BINDS'] = {}
app.config['SQLALCHEMY_BINDS']['traffic'] = 'sqlite:///traffic_data.db'

# 初始化数据库（只初始化一次，因为user_models和database_models共享同一个db实例）
db.init_app(app)
init_user_db(app)

# 初始化流量数据库表
with app.app_context():
    init_database_tables(app, bind_key='traffic')

# 注册用户管理蓝图
app.register_blueprint(user_bp)

# 注册数据库查询蓝图
app.register_blueprint(db_bp)

# 注册告警管理蓝图
app.register_blueprint(alert_bp)

# 注册配置管理蓝图
app.register_blueprint(config_bp)

# 初始化Swagger API文档
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "swagger",
            "route": "/api/docs/swagger.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs",
    "securityDefinitions": {
        "ApiKeyAuth": {
            "type": "apiKey",
            "name": "X-API-Key",
            "in": "header",
            "description": "API密钥认证，通过Header传递X-API-Key"
        },
        "ApiKeyQuery": {
            "type": "apiKey",
            "name": "api_key",
            "in": "query",
            "description": "API密钥认证，通过查询参数传递api_key"
        },
        "SessionAuth": {
            "type": "apiKey",
            "name": "session",
            "in": "cookie",
            "description": "Session认证，通过Cookie传递session"
        }
    }
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Bandix Monitor API",
        "description": "OpenWrt Bandix 流量监控 API 服务文档\n\n提供HTTP API接口来获取监控数据、管理用户、查询历史数据和告警管理。",
        "version": "1.0.0",
        "contact": {
            "name": "Bandix Monitor"
        }
    },
    "tags": [
        {
            "name": "用户管理",
            "description": "用户注册、登录、Token管理等接口"
        },
        {
            "name": "监控数据",
            "description": "获取实时监控数据接口"
        },
        {
            "name": "数据查询",
            "description": "查询历史流量数据接口"
        },
        {
            "name": "告警管理",
            "description": "告警规则和历史管理接口"
        },
        {
            "name": "系统信息",
            "description": "系统信息和健康检查接口"
        }
    ],
    "schemes": ["http", "https"]
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# 加载配置
CONFIG_FILE = os.getenv("BANDIX_CONFIG", os.path.join(os.path.dirname(__file__), "config", "bandix_config.ini"))


def load_api_config(config_file):
    """
    加载配置文件（包含 API 配置）
    """
    import configparser
    
    if not os.path.exists(config_file):
        return {}, {}
    
    config = configparser.ConfigParser()
    try:
        config.read(config_file, encoding='utf-8')
    except Exception as e:
        print(f"警告: 无法读取配置文件 '{config_file}': {e}，将使用默认配置", file=sys.stderr)
        return {}, {}
    
    bandix_config = {}
    if "bandix" in config:
        bandix_config = dict(config["bandix"])
    
    api_config = {}
    if "api" in config:
        api_config = dict(config["api"])
    
    return bandix_config, api_config


def reload_app_config():
    """
    重新加载应用配置
    """
    global bandix_config, api_config, monitor
    
    # 重新加载配置文件
    bandix_config, api_config = load_api_config(CONFIG_FILE)
    
    # 如果监控器已创建，需要重新创建以应用新配置
    if monitor is not None:
        monitor = None  # 重置监控器，下次调用get_monitor()时会重新创建
    
    print("应用配置已重新加载")


# 加载配置
bandix_config, api_config = load_api_config(CONFIG_FILE)

# 创建监控器实例（单例模式）
monitor = None


def check_auth():
    """
    检查 API 密钥认证（支持用户token和配置密钥两种方式）
    
    Returns:
        tuple: (is_valid, error_message, user_id)
    """
    auth_enabled = api_config.get("auth_enabled", "false").lower() == "true"
    
    # 如果未启用鉴权，直接通过
    if not auth_enabled:
        return True, None, None
    
    # 从请求中获取 token（支持 Header 和查询参数两种方式）
    token = None
    
    # 方式1: 从 Header 中获取
    token = request.headers.get("X-API-Key") or request.headers.get("Authorization")
    
    # 方式2: 从查询参数中获取
    if not token:
        token = request.args.get("api_key") or request.args.get("token")
    
    # 如果Authorization header以Bearer开头，提取token
    if token and token.startswith("Bearer "):
        token = token[7:]
    
    if not token:
        return False, "缺少 API 密钥，请在 Header 中添加 X-API-Key 或在查询参数中添加 api_key", None
    
    # 优先验证用户token
    user = User.query.filter_by(token=token, is_active=True).first()
    if user:
        return True, None, user.id
    
    # 如果用户token不存在，尝试验证配置的API密钥（向后兼容）
    configured_api_key = api_config.get("api_key", "").strip()
    if configured_api_key and token == configured_api_key:
        return True, None, None
    
    return False, "无效的 API 密钥或 Token", None


def require_auth(f):
    """
    API 鉴权装饰器
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        is_valid, error_msg, user_id = check_auth()
        if not is_valid:
            return jsonify({
                "success": False,
                "data": None,
                "error": error_msg
            }), 401
        # 将user_id存储到request上下文（可选）
        request.user_id = user_id
        return f(*args, **kwargs)
    return decorated_function


def get_monitor():
    """
    获取或创建监控器实例
    """
    global monitor
    if monitor is None:
        url = bandix_config.get("url", "http://10.0.0.1/ubus")
        username = bandix_config.get("username", "root")
        password = bandix_config.get("password", "password")
        # 优先使用环境变量，其次使用配置文件
        debug_env = os.getenv("DEBUG", "").lower()
        if debug_env:
            debug = debug_env == "true"
        else:
            debug = api_config.get("debug", "false").lower() == "true"
        
        monitor = BandixMonitor(
            url=url,
            username=username,
            password=password,
            debug=debug
        )
    return monitor


@app.route("/")
def index():
    """
    用户中心首页
    """
    try:
        return render_template('index.html')
    except Exception as e:
        # 如果模板不存在，返回API信息
        return jsonify({
            "name": "Bandix Monitor API",
            "version": "1.0.0",
            "message": "访问 /api/info 查看API信息",
            "error": str(e)
        })


@app.route("/data")
def data_query():
    """
    数据查询页面
    """
    try:
        return render_template('data_query.html')
    except Exception as e:
        return jsonify({
            "error": f"模板加载失败: {str(e)}"
        }), 500


@app.route("/api/info", methods=["GET"])
def api_info():
    """
    API信息端点
    ---
    tags:
      - 系统信息
    summary: 获取API信息
    description: 返回API的基本信息和所有可用端点
    produces:
      - application/json
    responses:
      200:
        description: 成功返回API信息
        schema:
          type: object
          properties:
            name:
              type: string
              example: "Bandix Monitor API"
            version:
              type: string
              example: "1.0.0"
            auth_enabled:
              type: boolean
              example: true
            endpoints:
              type: object
              description: 所有可用的API端点
            authentication:
              type: object
              description: 认证配置信息
    """
    auth_enabled = api_config.get("auth_enabled", "false").lower() == "true"
    health_check_require_auth = api_config.get("health_check_require_auth", "false").lower() == "true"
    
    return jsonify({
        "name": "Bandix Monitor API",
        "version": "1.0.0",
        "auth_enabled": auth_enabled,
        "endpoints": {
            "/": "用户中心",
            "/data": "数据查询页面",
            "/api/info": "API 说明",
            "/api/health": "健康检查" + ("（需要认证）" if health_check_require_auth else ""),
            "/api/monitor": "获取所有监控数据（全网+设备列表）" + ("（需要认证）" if auth_enabled else ""),
            "/api/monitor/total": "仅获取全网总计数据" + ("（需要认证）" if auth_enabled else ""),
            "/api/monitor/devices": "仅获取设备列表数据" + ("（需要认证）" if auth_enabled else ""),
            "/api/user/*": "用户管理API",
            "/api/database/*": "数据查询API"
        },
        "authentication": {
            "required": auth_enabled,
            "methods": [
                "Header: X-API-Key",
                "Query Parameter: api_key"
            ]
        } if auth_enabled else {
            "required": False
        }
    })


@app.route("/api/health", methods=["GET"])
def health():
    """
    健康检查端点
    ---
    tags:
      - 系统信息
    summary: 健康检查
    description: 检查API服务是否正常运行，根据配置可能需要认证
    security:
      - ApiKeyAuth: []
      - ApiKeyQuery: []
    produces:
      - application/json
    responses:
      200:
        description: 服务正常
        schema:
          type: object
          properties:
            status:
              type: string
              example: "healthy"
            service:
              type: string
              example: "bandix-monitor-api"
      401:
        description: 未授权（如果配置要求认证）
        schema:
          type: object
          properties:
            status:
              type: string
              example: "unauthorized"
            error:
              type: string
              example: "缺少 API 密钥"
    """
    # 根据配置决定是否需要鉴权
    health_check_require_auth = api_config.get("health_check_require_auth", "false").lower() == "true"
    
    if health_check_require_auth:
        is_valid, error_msg, _ = check_auth()
        if not is_valid:
            return jsonify({
                "status": "unauthorized",
                "error": error_msg
            }), 401
    
    return jsonify({
        "status": "healthy",
        "service": "bandix-monitor-api"
    })


@app.route("/favicon.ico")
def favicon():
    """返回favicon（避免404错误）"""
    from flask import Response
    return Response(status=204)  # No Content - 告诉浏览器没有favicon


@app.route("/api/monitor", methods=["GET"])
@require_auth
def get_monitor_data():
    """
    获取监控数据
    ---
    tags:
      - 监控数据
    summary: 获取所有监控数据
    description: 获取OpenWrt设备的实时监控数据，包括全网总计和所有设备列表
    security:
      - ApiKeyAuth: []
      - ApiKeyQuery: []
    produces:
      - application/json
    responses:
      200:
        description: 成功返回监控数据
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                total:
                  type: object
                  description: 全网总计流量数据
                devices:
                  type: array
                  description: 设备列表
                  items:
                    type: object
            error:
              type: string
              nullable: true
              example: null
      401:
        description: 未授权
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            data:
              type: object
              nullable: true
              example: null
            error:
              type: string
              example: "缺少 API 密钥"
      500:
        description: 服务器内部错误
    """
    try:
        monitor_instance = get_monitor()
        data = monitor_instance.get_monitor_data()
        
        if data is None:
            return jsonify({
                "success": False,
                "data": None,
                "error": "无法获取监控数据，请检查登录信息"
            }), 500
        
        return jsonify({
            "success": True,
            "data": data,
            "error": None
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "data": None,
            "error": str(e)
        }), 500


@app.route("/api/monitor/total", methods=["GET"])
@require_auth
def get_total_data():
    """
    获取全网总计数据
    ---
    tags:
      - 监控数据
    summary: 获取全网总计数据
    description: 仅获取全网总计的流量数据，不包含设备列表
    security:
      - ApiKeyAuth: []
      - ApiKeyQuery: []
    produces:
      - application/json
    responses:
      200:
        description: 成功返回全网总计数据
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              description: 全网总计流量数据
              properties:
                hostname:
                  type: string
                  example: "全网总计"
                down_speed:
                  type: object
                up_speed:
                  type: object
                total_download:
                  type: object
                total_upload:
                  type: object
            error:
              type: string
              nullable: true
              example: null
      401:
        description: 未授权
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            data:
              type: object
              nullable: true
              example: null
            error:
              type: string
              example: "缺少 API 密钥"
      500:
        description: 服务器内部错误
    """
    try:
        monitor_instance = get_monitor()
        data = monitor_instance.get_monitor_data()
        
        if data is None:
            return jsonify({
                "success": False,
                "data": None,
                "error": "无法获取监控数据，请检查登录信息"
            }), 500
        
        return jsonify({
            "success": True,
            "data": data.get("total"),
            "error": None
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "data": None,
            "error": str(e)
        }), 500


@app.route("/api/monitor/devices", methods=["GET"])
@require_auth
def get_devices_data():
    """
    获取设备列表数据
    ---
    tags:
      - 监控数据
    summary: 获取设备列表数据
    description: 仅获取所有设备的流量数据，不包含全网总计
    security:
      - ApiKeyAuth: []
      - ApiKeyQuery: []
    produces:
      - application/json
    responses:
      200:
        description: 成功返回设备列表数据
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: array
              description: 设备列表
              items:
                type: object
                properties:
                  hostname:
                    type: string
                    example: "device1"
                  ip:
                    type: string
                    example: "192.168.1.100"
                  mac:
                    type: string
                    example: "aa:bb:cc:dd:ee:ff"
                  down_speed:
                    type: object
                  up_speed:
                    type: object
            error:
              type: string
              nullable: true
              example: null
      401:
        description: 未授权
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            data:
              type: object
              nullable: true
              example: null
            error:
              type: string
              example: "缺少 API 密钥"
      500:
        description: 服务器内部错误
    """
    try:
        monitor_instance = get_monitor()
        data = monitor_instance.get_monitor_data()
        
        if data is None:
            return jsonify({
                "success": False,
                "data": None,
                "error": "无法获取监控数据，请检查登录信息"
            }), 500
        
        return jsonify({
            "success": True,
            "data": data.get("devices", []),
            "error": None
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "data": None,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    # 配置优先级：环境变量 > 配置文件 > 默认值
    host = os.getenv("API_HOST") or api_config.get("host", "0.0.0.0")
    
    port_env = os.getenv("API_PORT")
    port = int(port_env) if port_env else int(api_config.get("port", "5000"))
    
    debug_env = os.getenv("DEBUG", "").lower()
    if debug_env:
        debug = debug_env == "true"
    else:
        debug = api_config.get("debug", "false").lower() == "true"
    
    print(f"启动 Bandix Monitor API 服务...")
    print(f"监听地址: http://{host}:{port}")
    print(f"API 端点: http://{host}:{port}/api/monitor")
    print(f"调试模式: {'启用' if debug else '禁用'}")
    
    # 启动数据收集服务（自动启动，使用配置的API密钥）
    print(f"启动数据收集服务（每1秒收集一次）...")
    try:
        start_collector()
        print("数据收集服务已启动")
    except Exception as e:
        print(f"警告: 数据收集服务启动失败: {e}", file=sys.stderr)
    
    app.run(host=host, port=port, debug=debug)

