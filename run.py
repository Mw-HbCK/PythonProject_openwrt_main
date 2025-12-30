#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bandix Monitor API 启动脚本
"""
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app.bandix_api import app
from app.services.data_collector import start_collector

if __name__ == "__main__":
    # 从环境变量获取参数，如果没有则使用默认值
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "5000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    print(f"启动 Bandix Monitor API 服务...")
    print(f"监听地址: http://{host}:{port}")
    print(f"用户中心: http://{host}:{port}/")
    print(f"数据查询: http://{host}:{port}/data")
    
    # 启动数据收集服务（自动启动，使用配置的API密钥）
    print(f"启动数据收集服务（每1秒收集一次）...")
    try:
        start_collector()
        print("数据收集服务已启动")
    except Exception as e:
        print(f"警告: 数据收集服务启动失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    
    app.run(host=host, port=port, debug=debug)

