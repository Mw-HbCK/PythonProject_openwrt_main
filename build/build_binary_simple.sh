#!/bin/bash
# 简化版打包脚本 - 直接使用 PyInstaller 命令

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build"
DIST_DIR="${BUILD_DIR}/dist"

echo "开始打包 Bandix Monitor..."

# 安装 PyInstaller（如果未安装）
if ! command -v pyinstaller &> /dev/null; then
    echo "安装 PyInstaller..."
    pip install pyinstaller
fi

# 清理之前的构建
rm -rf "${BUILD_DIR}/build" "${DIST_DIR}" "${BUILD_DIR}/*.spec"

# 运行 PyInstaller
cd "${PROJECT_ROOT}"

pyinstaller \
    --name bandix-monitor \
    --onefile \
    --console \
    --add-data "app/config:app/config" \
    --add-data "app/templates:app/templates" \
    --hidden-import flask \
    --hidden-import flask_sqlalchemy \
    --hidden-import flasgger \
    --hidden-import werkzeug \
    --hidden-import pymysql \
    --hidden-import sqlalchemy \
    --hidden-import requests \
    --hidden-import schedule \
    --hidden-import boto3 \
    --hidden-import oss2 \
    --hidden-import reportlab \
    --hidden-import matplotlib \
    --hidden-import openpyxl \
    --hidden-import PIL \
    --hidden-import app \
    --hidden-import app.api \
    --hidden-import app.models \
    --hidden-import app.services \
    --hidden-import app.utils \
    --hidden-import jinja2 \
    --hidden-import configparser \
    --collect-all flask \
    --collect-all werkzeug \
    --collect-all jinja2 \
    --clean \
    --noconfirm \
    run.py

echo "打包完成！"
echo "可执行文件位于: ${DIST_DIR}/bandix-monitor"

