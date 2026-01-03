# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 配置文件
# 用于将 Bandix Monitor 打包成二进制文件

import os
import sys
from pathlib import Path

# 项目根目录（相对于 spec 文件）
spec_dir = Path(SPECPATH)
project_root = spec_dir.parent.parent

# 分析主程序
a = Analysis(
    ['run.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # 包含配置文件
        (str(project_root / 'app' / 'config'), 'app/config'),
        # 包含模板文件
        (str(project_root / 'app' / 'templates'), 'app/templates'),
    ] + ([
        # 包含静态文件（如果存在）
        (str(project_root / 'app' / 'static'), 'app/static'),
    ] if (project_root / 'app' / 'static').exists() else []),
    hiddenimports=[
        # Flask 相关
        'flask',
        'flask_sqlalchemy',
        'flasgger',
        'werkzeug',
        # 数据库相关
        'pymysql',
        'sqlalchemy',
        # 其他依赖
        'requests',
        'schedule',
        'boto3',
        'oss2',
        'reportlab',
        'matplotlib',
        'openpyxl',
        'PIL',
        'telegram',
        # 应用模块
        'app',
        'app.api',
        'app.models',
        'app.services',
        'app.utils',
        # 具体模块
        'app.bandix_api',
        'app.api.user_api',
        'app.api.database_api',
        'app.api.alert_api',
        'app.api.config_api',
        'app.api.backup_api',
        'app.api.report_api',
        'app.api.log_api',
        'app.api.stats_api',
        'app.api.mysql_api',
        'app.models.user_models',
        'app.models.database_models',
        'app.models.alert_models',
        'app.models.backup_models',
        'app.models.report_models',
        'app.models.api_stats_models',
        'app.services.bandix_monitor',
        'app.services.data_collector',
        'app.services.alert_checker',
        'app.services.config_manager',
        'app.services.notification_queue',
        'app.services.notification_service',
        'app.services.backup_service',
        'app.services.backup_scheduler',
        'app.services.report_service',
        'app.services.report_scheduler',
        'app.services.database_config_service',
        'app.services.logger_service',
        'app.utils.logger',
        # Jinja2 模板引擎
        'jinja2',
        'jinja2.ext',
        # 其他可能需要的模块
        'configparser',
        'threading',
        'queue',
        'datetime',
        'json',
        'hashlib',
        'secrets',
        'bcrypt',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib.tests',
        'numpy.tests',
        'pandas.tests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,  # 不使用加密
    noarchive=False,
)

# 创建 PYZ 文件
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# 创建可执行文件
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='bandix-monitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 显示控制台窗口（用于日志输出）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加图标文件路径
)

