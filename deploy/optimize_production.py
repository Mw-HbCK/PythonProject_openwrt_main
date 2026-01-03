# -*- coding: utf-8 -*-
"""
生产环境优化脚本
用于检查和优化生产环境配置
"""
import os
import sys
import configparser
from pathlib import Path

def check_production_config():
    """检查生产环境配置"""
    issues = []
    warnings = []
    
    # 检查配置文件
    config_path = Path(__file__).parent.parent / "app" / "config" / "bandix_config.ini"
    
    if not config_path.exists():
        issues.append(f"配置文件不存在: {config_path}")
        return issues, warnings
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    # 检查 API 配置
    if config.has_section('api'):
        if config.get('api', 'debug', fallback='false').lower() == 'true':
            warnings.append("生产环境不应启用 debug 模式")
        
        api_key = config.get('api', 'api_key', fallback='')
        if api_key in ['your-api-key', 'hanbo123', '']:
            issues.append("请修改默认 API Key")
    
    # 检查数据库配置
    if config.has_section('database'):
        mysql_password = config.get('database', 'mysql_password', fallback='')
        if mysql_password in ['password', '@HanBo123', '']:
            warnings.append("请使用强密码保护数据库")
    
    # 检查 SECRET_KEY
    if not os.getenv('SECRET_KEY'):
        issues.append("未设置 SECRET_KEY 环境变量（生产环境必需）")
    
    return issues, warnings

def optimize_config_file():
    """优化配置文件"""
    config_path = Path(__file__).parent.parent / "app" / "config" / "bandix_config.ini"
    
    if not config_path.exists():
        print(f"配置文件不存在: {config_path}")
        return False
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    # 确保 debug 为 false
    if config.has_section('api'):
        config.set('api', 'debug', 'false')
    
    # 保存配置
    with open(config_path, 'w') as f:
        config.write(f)
    
    print("配置文件已优化")
    return True

if __name__ == '__main__':
    print("=" * 50)
    print("生产环境配置检查")
    print("=" * 50)
    
    issues, warnings = check_production_config()
    
    if issues:
        print("\n❌ 发现严重问题:")
        for issue in issues:
            print(f"  - {issue}")
    
    if warnings:
        print("\n⚠️  警告:")
        for warning in warnings:
            print(f"  - {warning}")
    
    if not issues and not warnings:
        print("\n✅ 配置检查通过")
    
    # 询问是否优化
    if issues or warnings:
        response = input("\n是否自动优化配置? (y/n): ")
        if response.lower() == 'y':
            optimize_config_file()

