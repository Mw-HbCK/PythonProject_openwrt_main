#!/bin/bash
# -*- coding: utf-8 -*-
# 二进制打包脚本 - Ubuntu 24.04
# 将 Bandix Monitor 打包成可执行二进制文件

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build"
DIST_DIR="${BUILD_DIR}/dist"
VENV_DIR="${BUILD_DIR}/venv"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Bandix Monitor 二进制打包脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查 Python 版本
echo -e "\n${YELLOW}[1/7] 检查 Python 版本...${NC}"
python3 --version
if [ $? -ne 0 ]; then
    echo -e "${RED}错误: 未找到 Python 3${NC}"
    exit 1
fi

# 创建构建目录
echo -e "\n${YELLOW}[2/7] 创建构建目录...${NC}"
mkdir -p "${BUILD_DIR}"
mkdir -p "${DIST_DIR}"

# 创建虚拟环境
echo -e "\n${YELLOW}[3/7] 创建 Python 虚拟环境...${NC}"
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
fi

# 激活虚拟环境
source "${VENV_DIR}/bin/activate"

# 升级 pip
echo -e "\n${YELLOW}[4/7] 升级 pip 和安装依赖...${NC}"
pip install --upgrade pip setuptools wheel

# 安装项目依赖
pip install -r "${PROJECT_ROOT}/requirements.txt"

# 安装 PyInstaller
pip install pyinstaller

# 清理之前的构建
echo -e "\n${YELLOW}[5/7] 清理之前的构建...${NC}"
rm -rf "${BUILD_DIR}/build"
rm -rf "${DIST_DIR}/*"
rm -rf "${BUILD_DIR}/*.spec"

# 运行 PyInstaller
echo -e "\n${YELLOW}[6/7] 运行 PyInstaller 打包...${NC}"
cd "${PROJECT_ROOT}"
pyinstaller \
    --clean \
    --noconfirm \
    --workpath "${BUILD_DIR}/build" \
    --distpath "${DIST_DIR}" \
    --specpath "${BUILD_DIR}" \
    "${BUILD_DIR}/pyinstaller.spec" || {
    echo -e "${RED}打包失败！${NC}"
    exit 1
}

# 创建部署包
echo -e "\n${YELLOW}[7/7] 创建部署包...${NC}"
DEPLOY_DIR="${DIST_DIR}/bandix-monitor"
mkdir -p "${DEPLOY_DIR}"

# 复制可执行文件
cp "${DIST_DIR}/bandix-monitor" "${DEPLOY_DIR}/"

# 创建必要的目录结构
mkdir -p "${DEPLOY_DIR}/app/config"
mkdir -p "${DEPLOY_DIR}/logs"
mkdir -p "${DEPLOY_DIR}/backups"
mkdir -p "${DEPLOY_DIR}/reports"
mkdir -p "${DEPLOY_DIR}/instance"

# 复制配置文件模板（如果不存在）
if [ ! -f "${DEPLOY_DIR}/app/config/bandix_config.ini" ]; then
    cp "${PROJECT_ROOT}/app/config/bandix_config.ini" "${DEPLOY_DIR}/app/config/" 2>/dev/null || \
    echo "# 配置文件将在首次运行时创建" > "${DEPLOY_DIR}/app/config/bandix_config.ini"
fi

# 创建启动脚本
cat > "${DEPLOY_DIR}/start.sh" <<'EOF'
#!/bin/bash
# Bandix Monitor 启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 设置环境变量
export FLASK_ENV=production
export PYTHONUNBUFFERED=1

# 创建必要目录
mkdir -p logs backups reports instance app/config

# 启动应用
./bandix-monitor "$@"
EOF

chmod +x "${DEPLOY_DIR}/start.sh"

# 创建 systemd 服务文件
cat > "${DEPLOY_DIR}/bandix-monitor.service" <<EOF
[Unit]
Description=Bandix Monitor Service
After=network.target mysql.service

[Service]
Type=simple
User=bandix
Group=bandix
WorkingDirectory=${DEPLOY_DIR}
Environment="FLASK_ENV=production"
Environment="PYTHONUNBUFFERED=1"
ExecStart=${DEPLOY_DIR}/bandix-monitor
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 创建 README
cat > "${DEPLOY_DIR}/README.txt" <<'EOF'
Bandix Monitor 二进制部署包
============================

文件说明：
---------
- bandix-monitor        : 主程序可执行文件
- start.sh              : 启动脚本
- bandix-monitor.service: systemd 服务配置文件
- app/config/           : 配置文件目录
- logs/                 : 日志目录
- backups/              : 备份目录
- reports/              : 报表目录
- instance/             : 数据库目录

快速开始：
---------
1. 解压部署包到目标目录
2. 编辑 app/config/bandix_config.ini 配置文件
3. 运行 ./start.sh 启动服务

或使用 systemd：
--------------
1. 复制 bandix-monitor.service 到 /etc/systemd/system/
2. 修改服务文件中的路径
3. sudo systemctl daemon-reload
4. sudo systemctl enable bandix-monitor
5. sudo systemctl start bandix-monitor

更多信息请参考部署文档。
EOF

# 创建压缩包
echo -e "\n${GREEN}创建部署压缩包...${NC}"
cd "${DIST_DIR}"
tar -czf "bandix-monitor-$(date +%Y%m%d-%H%M%S).tar.gz" bandix-monitor/

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}打包完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\n${YELLOW}输出文件：${NC}"
echo -e "  可执行文件: ${DEPLOY_DIR}/bandix-monitor"
echo -e "  部署包目录: ${DEPLOY_DIR}"
echo -e "  压缩包: ${DIST_DIR}/bandix-monitor-*.tar.gz"
echo -e "\n${YELLOW}下一步：${NC}"
echo -e "  1. 检查 ${DEPLOY_DIR} 目录"
echo -e "  2. 编辑配置文件: ${DEPLOY_DIR}/app/config/bandix_config.ini"
echo -e "  3. 将部署包复制到目标服务器"
echo -e "  4. 运行 ./start.sh 启动服务"
echo -e "\n"

