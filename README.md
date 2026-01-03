# Bandix Monitor - OpenWrt 流量监控系统

[![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

一个功能完整、现代化的 OpenWrt 路由器流量监控系统，提供实时监控、数据可视化、统计分析、告警管理等全方位功能。

## ✨ 主要特性

### 🎯 核心功能

- **📊 实时流量监控**
  - 实时获取 OpenWrt 设备的全网流量和设备流量数据
  - 实时监控仪表盘，支持自定义刷新间隔（1秒-30秒）
  - 设备在线状态监控
  - 流量排行榜（Top N 设备）

- **📈 数据可视化**
  - 流量趋势图（时间序列折线图）
    - 全网流量趋势（下行/上行）
    - 单设备流量趋势
    - 支持时间范围选择（今天/最近7天/最近30天）
  - 设备对比图（柱状图、饼图）
    - 设备流量对比
    - 设备流量占比分析

- **📉 统计分析**
  - 流量统计汇总（今日/本周/本月）
  - 速率统计（平均速率、峰值速率）
  - 设备排名分析
  - 设备活跃度分析
  - 时间段对比（同比/环比）

- **🔔 告警管理**
  - 流量阈值告警（设置流量上限）
  - 设备离线告警（设备长时间无流量）
  - 告警规则管理（创建、编辑、启用/禁用、删除）
  - 告警历史记录

- **🗄️ 数据管理**
  - 数据查询（分页查询，支持时间范围筛选）
  - 数据导出（CSV、Excel 格式）
  - 数据清理（按时间删除旧数据）
  - 数据库优化（VACUUM）
  - 数据备份（SQL 备份文件导出）
  
- **💾 定时数据备份**
  - 自动定时备份（每日/每周/每月）
  - 多数据库备份（用户数据库、流量数据库）
  - 备份文件压缩（ZIP格式）
  - 备份历史记录管理
  - 备份文件下载和恢复
  - 云存储支持（AWS S3、阿里云OSS，可选）
  - 自动清理旧备份

- **👥 用户管理**
  - 用户注册/登录
  - Token 管理（生成、刷新）
  - 基于角色的权限控制（管理员/普通用户）
  - 用户管理界面（管理员功能）

- **⚙️ 配置管理**
  - Web 界面管理配置
  - API 密钥管理
  - 数据收集间隔设置
  - 配置热重载

- **🎨 现代化 UI**
  - 响应式设计（支持移动端）
  - 暗色主题支持
  - 美化的滚动条
  - 侧边栏导航
  - 直观的数据展示

- **📚 API 文档**
  - 完整的 Swagger/OpenAPI 文档
  - 交互式 API 文档页面（`/api/docs`）
  - 所有 API 端点已添加详细注释

## 🛠️ 技术栈

### 后端

- **Flask 2.3+** - Web 框架
- **SQLAlchemy 3.0+** - ORM 数据库操作
- **SQLite** - 轻量级数据库
- **Flasgger 0.9.7+** - Swagger API 文档生成
- **Requests 2.28+** - HTTP 请求库（用于 OpenWrt 通信）

### 前端

- **HTML5/CSS3** - 现代化响应式设计
- **JavaScript (ES6+)** - 前端交互逻辑
- **Chart.js** - 数据可视化图表库
- **SheetJS (xlsx)** - Excel 导出功能

### 架构特点

- RESTful API 设计
- 模块化代码结构
- 基于角色的访问控制（RBAC）
- Token 认证机制
- 自动数据收集服务

## 📁 项目结构

```
bandix-monitor/
├── app/                          # 应用主目录
│   ├── __init__.py
│   ├── bandix_api.py            # Flask 应用主入口
│   │
│   ├── api/                     # API 路由模块
│   │   ├── __init__.py
│   │   ├── user_api.py          # 用户管理 API（注册、登录、Token、用户管理）
│   │   ├── database_api.py      # 数据查询 API（流量数据、统计、图表）
│   │   ├── alert_api.py         # 告警管理 API（规则、历史）
│   │   └── config_api.py        # 配置管理 API
│   │
│   ├── models/                  # 数据模型模块
│   │   ├── __init__.py
│   │   ├── user_models.py       # 用户数据模型（users.db）
│   │   ├── database_models.py   # 流量数据模型（traffic_data.db）
│   │   └── alert_models.py      # 告警数据模型
│   │
│   ├── services/                # 业务逻辑服务模块
│   │   ├── __init__.py
│   │   ├── bandix_monitor.py    # OpenWrt 设备通信服务
│   │   ├── data_collector.py    # 数据收集服务（定时存储）
│   │   ├── alert_checker.py     # 告警检查服务
│   │   └── config_manager.py    # 配置管理服务
│   │
│   ├── templates/               # HTML 模板
│   │   ├── index.html           # 用户中心主页面（集成所有功能）
│   │   └── data_query.html      # 数据查询页面（旧版，可选）
│   │
│   └── config/                  # 配置文件
│       └── bandix_config.ini    # 主配置文件
│
├── instance/                    # 数据库文件目录（自动创建）
│   ├── users.db                # 用户和 Token 数据库
│   └── traffic_data.db         # 流量历史数据数据库
│
├── deprecated/                  # 废弃文件目录（历史参考）
│
├── requirements.txt             # Python 依赖包
├── run.py                      # 启动脚本
├── FEATURE_ROADMAP.md          # 功能路线图
└── README.md                   # 本文件
```

## 🚀 快速开始

### 前置要求

- Python 3.6 或更高版本
- OpenWrt 路由器（支持 ubus API）
- 网络连接（能够访问 OpenWrt 设备）

### 1. 安装依赖

```bash
# 克隆项目（如果有 Git 仓库）
# git clone <repository-url>
# cd bandix-monitor

# 安装 Python 依赖
pip install -r requirements.txt
```

### 2. 配置

编辑 `app/config/bandix_config.ini`，配置 OpenWrt 设备连接信息：

```ini
[bandix]
# OpenWrt 设备的 ubus URL
url = http://10.0.0.1/ubus

# 登录用户名
username = root

# 登录密码
password = your-password

[api]
# API 服务监听地址
host = 0.0.0.0

# API 服务端口
port = 5000

# 是否启用调试模式
debug = false

# API 鉴权配置
auth_enabled = true
api_key = your-api-key
health_check_require_auth = false

[collector]
# 数据收集间隔（秒）
collect_interval = 1.0
```

### 3. 初始化数据库

数据库会在首次运行时自动创建，无需手动初始化。

如果需要手动创建默认管理员账户，可以通过注册功能创建，或使用以下 Python 脚本：

```python
from app.bandix_api import app
from app.models.user_models import db, User
with app.app_context():
    db.create_all()
    admin = User(username='admin', role='admin', is_active=True)
    admin.set_password('your-password')
    db.session.add(admin)
    db.session.commit()
```

### 4. 启动服务

**方式一：使用启动脚本（推荐）**

```bash
python run.py
```

**方式二：直接运行 Flask 应用**

```bash
python app/bandix_api.py
```

**方式三：使用 Flask 开发服务器**

```bash
export FLASK_APP=app.bandix_api
flask run --host=0.0.0.0 --port=5000
```

启动后，你会看到以下信息：

```
启动 Bandix Monitor API 服务...
监听地址: http://0.0.0.0:5000
用户中心: http://0.0.0.0:5000/
数据查询: http://0.0.0.0:5000/data
启动数据收集服务（每1秒收集一次）...
数据收集服务已启动
启动通知任务队列...
通知任务队列已启动
启动备份调度器...
备份调度器已启动
```

**注意**：
- 通知功能使用内置的线程队列处理，无需额外启动独立服务
- 备份调度器会在启动时检查配置，如果备份未启用则不会启动

### 5. 访问应用

- **用户中心（主界面）**: http://localhost:5000/
- **API 文档（Swagger）**: http://localhost:5000/api/docs
- **数据查询（旧版）**: http://localhost:5000/data

### 6. 首次使用

1. 访问用户中心（http://localhost:5000/）
2. 注册一个新账户（第一个注册的用户会被自动设置为管理员）
3. 登录后可以：
   - 查看实时监控数据
   - 查询历史数据
   - 查看统计分析和图表
   - 管理告警规则（管理员）
   - 管理用户（管理员）
   - 管理系统配置（管理员）

## 📖 功能详解

### 实时监控仪表盘

- **实时流量显示**：当前全网下行/上行速率、总流量
- **设备状态**：设备在线/离线状态、最后活跃时间
- **流量排行榜**：按流量大小排序的设备列表
- **系统状态**：数据收集服务状态、数据库统计信息
- **自动刷新**：支持 1秒/2秒/5秒/10秒/30秒/手动刷新

### 数据查询

- **查询类型**：
  - 全网流量数据
  - 设备流量数据
  - 设备列表
- **筛选功能**：
  - 时间范围选择
  - 设备选择
  - 分页浏览（每页可自定义）
- **导出功能**：
  - CSV 格式导出
  - Excel 格式导出

### 数据可视化

- **流量趋势图**：
  - 全网流量趋势（支持今天/最近7天/最近30天）
  - 单设备流量趋势
  - 实时流量曲线图
- **设备对比图**：
  - 设备流量对比（柱状图）
  - 设备流量占比（饼图）

### 统计分析

- **流量统计汇总**：
  - 今日/本周/本月流量统计
  - 总下载/总上传流量
- **速率统计**：
  - 平均下行/上行速率
  - 峰值下行/上行速率（含时间）
- **设备统计**：
  - 设备流量排名（Top 10）
  - 设备活跃度（24小时/7天）
  - 设备流量占比
- **时间段对比**：
  - 日环比、周环比、月环比分析

### 告警管理

- **告警类型**：
  - 流量阈值告警（设置流量上限，字节/秒）
  - 设备离线告警（设备超过设定时间无流量）
- **告警规则管理**：
  - 创建、编辑、删除告警规则
  - 启用/禁用告警规则
  - 设置告警严重程度（信息/警告/严重）
- **告警历史**：
  - 查看历史告警记录
  - 按类型、严重程度筛选
  - 标记已读/未读

### 用户管理（管理员功能）

- **用户列表**：查看所有用户
- **用户操作**：
  - 创建新用户
  - 编辑用户信息
  - 启用/禁用用户
  - 删除用户
- **权限控制**：
  - 用户角色（管理员/普通用户）
  - 基于角色的功能访问控制

### 数据管理（管理员功能）

- **数据清理**：
  - 按时间删除旧数据（保留最近 N 天）
  - 手动清理指定时间范围（支持预览）
- **数据库优化**：
  - VACUUM 操作（压缩数据库，释放空间）
- **数据备份**：
  - 导出数据库为 SQL 备份文件
  - 查看备份信息（数据库大小、记录数）

### 配置管理（管理员功能）

- **配置查看**：查看当前系统配置
- **配置编辑**：
  - 修改 OpenWrt 连接配置
  - 修改 API 配置
  - 修改数据收集间隔
- **配置重载**：配置修改后自动重载（无需重启服务）

## 🔌 API 使用

### 认证方式

API 支持两种认证方式：

1. **Token 认证（推荐）**：通过用户登录获取 Token
   ```bash
   # 在 Header 中传递 Token
   curl -H "X-API-Key: your-token" http://localhost:5000/api/monitor
   ```

2. **API Key 认证**：使用配置文件中的 API Key
   ```bash
   # 在 Header 中传递 API Key
   curl -H "X-API-Key: your-api-key" http://localhost:5000/api/monitor
   
   # 或使用查询参数
   curl http://localhost:5000/api/monitor?api_key=your-api-key
   ```

### 主要 API 端点

#### 用户管理

- `POST /api/user/register` - 用户注册
- `POST /api/user/login` - 用户登录
- `POST /api/user/logout` - 退出登录
- `GET /api/user/info` - 获取用户信息
- `POST /api/user/token/refresh` - 刷新 Token
- `GET /api/user/list` - 获取用户列表（管理员）
- `PUT /api/user/<user_id>` - 更新用户（管理员）
- `POST /api/user/<user_id>/toggle` - 启用/禁用用户（管理员）
- `DELETE /api/user/<user_id>` - 删除用户（管理员）

#### 实时监控

- `GET /api/monitor` - 获取实时监控数据（全网+设备）
- `GET /api/monitor/total` - 获取全网实时流量
- `GET /api/monitor/devices` - 获取设备实时流量

#### 数据查询

- `GET /api/database/devices` - 获取设备列表
- `GET /api/database/total-traffic` - 查询全网流量数据
- `GET /api/database/device-traffic/<device_id>` - 查询设备流量数据
- `GET /api/database/stats` - 获取统计信息
- `GET /api/database/charts/traffic-trend` - 获取流量趋势数据
- `GET /api/database/charts/device-comparison` - 获取设备对比数据

#### 告警管理

- `GET /api/alerts/rules` - 获取告警规则列表
- `POST /api/alerts/rules` - 创建告警规则
- `GET /api/alerts/rules/<rule_id>` - 获取告警规则详情
- `PUT /api/alerts/rules/<rule_id>` - 更新告警规则
- `POST /api/alerts/rules/<rule_id>/toggle` - 启用/禁用告警规则
- `DELETE /api/alerts/rules/<rule_id>` - 删除告警规则
- `GET /api/alerts/history` - 获取告警历史

#### 数据管理（管理员）

- `POST /api/database/management/cleanup` - 数据清理
- `POST /api/database/management/vacuum` - 数据库优化
- `GET /api/database/management/backup` - 导出数据库备份（手动备份）
- `GET /api/database/management/backup-info` - 获取备份信息

#### 备份管理 API（定时备份）

- `GET /api/backup/history` - 获取备份历史记录列表
- `GET /api/backup/download/<backup_id>` - 下载备份文件
- `POST /api/backup/manual` - 手动触发备份（管理员）
- `POST /api/backup/restore/<backup_id>` - 恢复备份（管理员，危险操作）
- `DELETE /api/backup/<backup_id>` - 删除备份文件（管理员）
- `GET /api/backup/config` - 获取备份配置
- `PUT /api/backup/config` - 更新备份配置（管理员）
- `POST /api/backup/config/test` - 测试备份配置（管理员，测试云存储连接等）
- `GET /api/database/management/stats` - 获取数据库统计

#### 配置管理（管理员）

- `GET /api/config` - 获取配置信息
- `PUT /api/config` - 更新配置
- `GET /api/config/collector` - 获取数据收集器配置和状态
- `GET /api/config/notifications` - 获取通知配置
- `PUT /api/config/notifications` - 更新通知配置
- `POST /api/config/notifications/test` - 测试通知配置

### 完整 API 文档

访问交互式 API 文档页面查看完整的 API 说明：

http://localhost:5000/api/docs

## ⚙️ 配置说明

### 配置文件结构

`app/config/bandix_config.ini` 包含四个主要配置段：

#### [bandix] - OpenWrt 设备配置

```ini
url = http://10.0.0.1/ubus      # OpenWrt 设备的 ubus URL
username = root                  # 登录用户名
password = your-password         # 登录密码
```

#### [api] - API 服务配置

```ini
host = 0.0.0.0                  # 监听地址（0.0.0.0 表示监听所有网络接口）
port = 5000                      # 监听端口
debug = false                    # 调试模式（true/false）
auth_enabled = true              # 是否启用 API 认证
api_key = your-api-key          # API 密钥（用于 API Key 认证）
health_check_require_auth = false  # 健康检查端点是否需要认证
```

#### [collector] - 数据收集配置

```ini
collect_interval = 1.0           # 数据收集间隔（秒）
```

#### [notifications] - 通知配置

```ini
# 邮件通知配置
email_enabled = false            # 是否启用邮件通知
email_smtp_host = smtp.example.com  # SMTP服务器地址
email_smtp_port = 587            # SMTP端口
email_use_tls = true             # 是否使用TLS/SSL
email_username = your-email@example.com  # 邮箱用户名
email_password = your-password   # 邮箱密码
email_from = alerts@example.com  # 发件人地址
email_to = admin@example.com     # 收件人地址（多个用逗号或分号分隔）

# Webhook 通知配置
webhook_enabled = false          # 是否启用Webhook通知
webhook_urls = https://example.com/webhook  # Webhook URL（多个用分号分隔）
webhook_headers = {"Authorization": "Bearer token"}  # 请求头（JSON格式）

# Telegram 通知配置
telegram_enabled = false         # 是否启用Telegram通知
telegram_bot_token = your-bot-token  # Telegram Bot Token
telegram_chat_ids = 123456789;987654321  # Chat ID（多个用分号分隔）

# 企业微信通知配置
wecom_enabled = false            # 是否启用企业微信通知
wecom_webhook_urls = https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx  # Webhook URL（多个用分号分隔）

# 钉钉通知配置
dingtalk_enabled = false         # 是否启用钉钉通知
dingtalk_webhook_urls = https://oapi.dingtalk.com/robot/send?access_token=xxx  # Webhook URL（多个用分号分隔）

[backup]
# 定时备份配置
backup_enabled = false           # 是否启用定时备份
frequency = daily                # 备份频率：daily/weekly/monthly
backup_time = 02:00              # 备份时间（HH:MM格式，24小时制）
backup_dir = ./backups           # 备份文件存储目录
databases = users,traffic        # 要备份的数据库（用逗号分隔）
keep_count = 30                  # 保留最近N个备份文件
compress = true                  # 是否压缩备份文件（ZIP格式）

# 云存储配置（可选）
cloud_enabled = false            # 是否启用云存储上传
cloud_type = s3                  # 云存储类型：s3（AWS S3）或oss（阿里云OSS）
cloud_bucket = your-bucket-name  # 存储桶名称
cloud_region = us-east-1         # AWS S3 区域（使用S3时必填）
cloud_access_key = your-key      # 访问密钥
cloud_secret_key = your-secret   # 秘密密钥
cloud_endpoint = oss-cn-hangzhou.aliyuncs.com  # OSS端点（使用OSS时必填）
```

**Webhook URL 获取方法**：

- **企业微信**：
  1. 在企业微信群聊中，点击右上角"..." → "群机器人"
  2. 选择"添加机器人" → "自定义"
  3. 设置机器人名称和头像
  4. 复制生成的 Webhook URL

- **钉钉**：
  1. 在钉钉群聊中，点击"群设置" → "智能群助手" → "添加机器人"
  2. 选择"自定义"机器人
  3. 设置机器人名称，选择安全设置（建议选择"加签"）
  4. 复制生成的 Webhook URL（包含 access_token 参数）

### 环境变量

可以通过环境变量覆盖配置文件中的设置：

- `API_HOST` - API 服务监听地址（默认：0.0.0.0）
- `API_PORT` - API 服务端口（默认：5000）
- `DEBUG` - 调试模式（true/false）
- `BANDIX_CONFIG` - 配置文件路径（默认：app/config/bandix_config.ini）

示例：

```bash
export API_HOST=127.0.0.1
export API_PORT=8080
export DEBUG=true
python run.py
```

## 🗄️ 数据库

系统使用 SQLite 数据库，包含以下数据库文件：

### users.db - 用户数据库

- **users** - 用户表
  - id: 用户 ID
  - username: 用户名（唯一）
  - password_hash: 密码哈希
  - token: API Token
  - role: 用户角色（admin/user）
  - is_active: 是否启用
  - created_at: 创建时间
  - updated_at: 更新时间

### traffic_data.db - 流量数据库

- **devices** - 设备表
  - id: 设备 ID
  - mac: MAC 地址（唯一）
  - name: 设备名称
  - ip: IP 地址
  - created_at: 首次记录时间
  - updated_at: 最后更新时间

- **total_traffic** - 全网流量表
  - id: 记录 ID
  - timestamp: 时间戳
  - down_speed_bytes: 下行速率（字节/秒）
  - up_speed_bytes: 上行速率（字节/秒）
  - total_download_bytes: 总下载量（字节）
  - total_upload_bytes: 总上传量（字节）

- **device_traffic** - 设备流量表
  - id: 记录 ID
  - device_id: 设备 ID（外键）
  - timestamp: 时间戳
  - down_speed_bytes: 下行速率（字节/秒）
  - up_speed_bytes: 上行速率（字节/秒）
  - total_download_bytes: 总下载量（字节）
  - total_upload_bytes: 总上传量（字节）

### alert_rules.db - 告警数据库

- **alert_rules** - 告警规则表
  - id: 规则 ID
  - name: 规则名称
  - alert_type: 告警类型（traffic_threshold/device_offline）
  - enabled: 是否启用
  - severity: 严重程度（info/warning/critical）
  - threshold_bytes: 流量阈值（字节/秒）
  - offline_threshold_minutes: 离线阈值（分钟）
  - device_id: 设备 ID（可选，null 表示所有设备）
  - created_at: 创建时间
  - updated_at: 更新时间

- **alert_history** - 告警历史表
  - id: 记录 ID
  - rule_id: 规则 ID（外键）
  - alert_type: 告警类型
  - message: 告警消息
  - severity: 严重程度
  - is_read: 是否已读
  - triggered_at: 触发时间

## 🔒 安全说明

### 认证与授权

- **用户认证**：基于 Token 的认证机制
- **API 认证**：支持 Token 和 API Key 两种方式
- **权限控制**：基于角色的访问控制（RBAC）
  - 管理员：拥有所有功能权限
  - 普通用户：只能查看和导出数据

### 安全建议

1. **生产环境部署**：
   - 修改默认 API Key
   - 使用强密码
   - 启用 HTTPS（使用反向代理，如 Nginx）
   - 定期备份数据库

2. **密码安全**：
   - 密码使用 bcrypt 哈希存储
   - 建议使用强密码策略

3. **Token 安全**：
   - Token 存储在数据库中
   - 支持 Token 刷新机制
   - 退出登录时清除 Token

## 🚢 生产环境部署

### 使用 Gunicorn

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动服务
gunicorn -w 4 -b 0.0.0.0:5000 app.bandix_api:app
```

### 使用 Nginx 反向代理

Nginx 配置示例：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 使用 systemd 服务

创建 `/etc/systemd/system/bandix-monitor.service`：

```ini
[Unit]
Description=Bandix Monitor Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/bandix-monitor
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app.bandix_api:app
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable bandix-monitor
sudo systemctl start bandix-monitor
```

## 🐛 故障排查

### 常见问题

1. **无法连接 OpenWrt 设备**
   - 检查网络连接
   - 验证 ubus URL 是否正确
   - 检查用户名和密码
   - 确认 OpenWrt 设备允许 ubus API 访问

2. **数据收集服务未启动**
   - 检查配置文件中的 `collect_interval` 设置
   - 查看应用日志
   - 确认 API 服务正常运行

3. **数据库错误**
   - 检查数据库文件权限
   - 确认 SQLite 数据库文件未损坏
   - 尝试备份后重新初始化数据库

4. **API 认证失败**
   - 检查 Token 是否有效
   - 验证 API Key 是否正确
   - 确认认证功能已启用

### 日志查看

应用日志会输出到控制台。在生产环境中，建议将日志重定向到文件：

```bash
python run.py >> /var/log/bandix-monitor.log 2>&1
```

## 🔧 实现机制与原理

本节详细说明系统的核心实现机制和工作原理。

### 1. OpenWrt 通信机制

#### 1.1 ubus API 协议

系统通过 OpenWrt 的 `ubus` RPC 接口与路由器通信。ubus 是 OpenWrt 的微总线架构，提供进程间通信机制。

**通信流程**：

1. **登录认证**：
   ```python
   # 发送 JSON-RPC 2.0 格式的登录请求
   {
       "jsonrpc": "2.0",
       "id": 1,
       "method": "call",
       "params": [
           "00000000000000000000000000000000",  # 临时会话ID
           "session",                           # 命名空间
           "login",                             # 方法名
           {"username": "root", "password": "xxx"}
       ]
   }
   ```

2. **获取会话ID (SID)**：
   - 登录成功后，OpenWrt 返回一个唯一的会话ID
   - 后续所有请求都需要在 `params[0]` 位置传递此 SID

3. **获取流量数据**：
   ```python
   # 调用 luci.bandix.getMetrics 获取流量指标
   {
       "jsonrpc": "2.0",
       "id": 3,
       "method": "call",
       "params": [
           "<session_id>",      # 登录获取的会话ID
           "luci.bandix",       # 命名空间
           "getMetrics",        # 方法名
           {"mac": "all"}       # 参数：all表示所有设备
       ]
   }
   ```

4. **会话管理**：
   - SID 有时效性，系统会在需要时重新登录
   - 使用 `requests.Session()` 保持 HTTP 连接复用

#### 1.2 数据获取流程

`BandixMonitor` 类封装了所有 OpenWrt 通信逻辑：

- `login()`: 执行登录，获取 SID
- `get_status()`: 获取设备状态信息
- `get_metrics(mac="all")`: 获取流量数据
  - `mac="all"`: 获取全网流量
  - `mac="具体MAC地址"`: 获取指定设备流量

**返回数据格式**：
```python
{
    "total": {
        "down_speed": 1234567,      # 下行速率（字节/秒）
        "up_speed": 234567,         # 上行速率（字节/秒）
        "total_download": 1000000,  # 总下载量（字节）
        "total_upload": 500000      # 总上传量（字节）
    },
    "devices": [
        {
            "mac": "xx:xx:xx:xx:xx:xx",
            "name": "设备名称",
            "ip": "192.168.1.100",
            "down_speed": 123456,
            "up_speed": 23456,
            "total_download": 500000,
            "total_upload": 250000
        }
    ]
}
```

### 2. 数据收集机制

#### 2.1 后台线程架构

数据收集服务运行在独立的守护线程中，不会阻塞主应用：

```python
# 线程启动
COLLECTOR_THREAD = threading.Thread(target=collector_loop, daemon=True)
COLLECTOR_THREAD.start()
```

**关键特性**：
- **守护线程 (daemon=True)**：主进程退出时自动终止
- **独立运行**：与 Flask 主线程并行，互不干扰
- **可配置间隔**：支持动态调整收集间隔（默认1秒）

#### 2.2 数据收集流程

```
┌─────────────────┐
│   collector_loop │ 主循环
└────────┬────────┘
         │
         ├─► load_collect_interval_from_config()  # 读取配置（支持热更新）
         │
         ├─► collect_data_once()                  # 执行一次收集
         │   │
         │   ├─► GET /api/monitor (带Token认证)
         │   │
         │   ├─► save_traffic_data(data)          # 保存到数据库
         │   │   │
         │   │   ├─► 保存全网流量 → total_traffic 表
         │   │   └─► 保存设备流量 → device_traffic 表
         │   │       └─► 更新/创建设备记录 → devices 表
         │   │
         │   └─► 错误处理与日志记录
         │
         └─► time.sleep(COLLECT_INTERVAL)          # 等待下次收集
```

#### 2.3 数据库存储策略

**数据去重机制**：
- 同一时间戳的数据只保留一条记录
- 使用 `timestamp` 字段作为唯一性约束

**设备信息同步**：
- 首次发现设备时，自动创建设备记录
- 后续更新设备的 `updated_at` 时间戳
- MAC 地址作为设备的唯一标识

**数据聚合**：
- 原始数据按秒级粒度存储
- 查询时通过 SQL 聚合函数进行时间范围汇总
- 支持按小时、按天等粒度聚合

### 3. 实时监控机制

#### 3.1 轮询架构

前端使用 JavaScript `setInterval` 定时轮询 API：

```javascript
// 实时监控仪表盘
function initDashboard() {
    // 立即加载一次
    loadDashboardData();
    
    // 设置定时刷新
    const interval = parseInt(refreshIntervalSelect.value) * 1000;
    if (interval > 0) {
        dashboardInterval = setInterval(loadDashboardData, interval);
    }
}
```

**刷新间隔选项**：
- 1秒、2秒、5秒、10秒、30秒
- 手动刷新模式（interval = 0）

#### 3.2 数据更新流程

```
前端页面
  │
  ├─► 定时器触发
  │   │
  │   └─► fetch('/api/monitor')
  │       │
  │       ├─► 后端认证检查
  │       │
  │       ├─► BandixMonitor.get_all_metrics()
  │       │   │
  │       │   ├─► 检查会话有效性
  │       │   │
  │       │   ├─► 登录（如需要）
  │       │   │
  │       │   └─► 获取实时流量数据
  │       │
  │       └─► 返回JSON数据
  │
  └─► 更新UI（DOM操作）
      ├─► 更新流量卡片
      ├─► 更新设备列表
      └─► 更新系统状态
```

#### 3.3 性能优化

- **连接复用**：使用 `requests.Session()` 保持HTTP连接
- **请求超时**：设置10秒超时，避免长时间等待
- **错误处理**：网络错误时显示友好提示，不影响页面使用
- **数据缓存**：前端可选择性缓存设备列表等静态数据

### 4. 告警系统机制

#### 4.1 告警检查架构

告警检查在数据收集线程中周期性执行：

```python
# 数据收集后触发告警检查
def collector_loop():
    while IS_RUNNING:
        collect_data_once()          # 收集数据
        check_alerts(app)            # 检查告警（可选）
        time.sleep(COLLECT_INTERVAL)
```

#### 4.2 告警类型与检查逻辑

**流量阈值告警**：

1. 获取所有启用的流量阈值规则
2. 获取最新的流量数据（全网或指定设备）
3. 比较当前速率与阈值：
   ```python
   if current_speed >= threshold_bytes:
       # 触发告警
       create_alert_history(rule, message, severity)
   ```
4. **防重复机制**：检查5分钟内是否已有相同规则的告警，避免频繁触发

**设备离线告警**：

1. 获取所有启用的离线告警规则
2. 遍历所有设备，检查最后活动时间：
   ```python
   threshold_time = now - timedelta(minutes=offline_threshold_minutes)
   if device.updated_at < threshold_time:
       # 设备离线
       create_alert_history(rule, message, severity)
   ```
3. **设备过滤**：如果规则指定了特定设备ID，只检查该设备

#### 4.3 告警历史管理

- **状态管理**：告警有 `triggered`（已触发）和 `acknowledged`（已确认）两种状态
- **历史记录**：所有告警都记录在 `alert_history` 表中
- **告警展示**：前端可以筛选未读告警、按类型分类显示

### 5. 认证与授权机制

#### 5.1 双认证体系

系统支持两种认证方式：

**1. Token 认证（推荐）**：
- 用户登录后生成唯一的 Token（使用 `secrets.token_urlsafe(48)`）
- Token 存储在 `users.token` 字段中
- 前端在请求头中携带：`X-API-Key: <token>`

**2. API Key 认证（向后兼容）**：
- 配置文件中的 `api_key` 字段
- 适用于脚本调用等场景

**认证优先级**：
```python
def check_auth():
    # 1. 优先检查用户Token
    user = User.query.filter_by(token=token, is_active=True).first()
    if user:
        return True, None, user.id
    
    # 2. 其次检查API Key
    if token == configured_api_key:
        return True, None, None
    
    return False, "认证失败", None
```

#### 5.2 会话管理（Web界面）

Web界面使用 Flask Session：

- 用户登录成功后，在 Session 中存储 `user_id`
- 后续请求通过 `@login_required` 装饰器验证 Session
- 退出登录时清除 Session

**装饰器实现**：
```python
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function
```

#### 5.3 基于角色的访问控制（RBAC）

**角色定义**：
- `admin`：管理员，拥有所有权限
- `user`：普通用户，只能查看和导出数据

**权限检查装饰器**：
```python
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin():
            return jsonify({'success': False, 'message': '需要管理员权限'}), 403
        
        return f(*args, **kwargs)
    return decorated_function
```

**前端权限控制**：
- 根据用户角色动态显示/隐藏功能按钮
- 管理员可以看到：配置管理、用户管理、数据管理等标签页

### 6. 数据存储机制

#### 6.1 数据库设计原则

**分离存储**：
- `users.db`：用户相关数据（用户表、会话等）
- `traffic_data.db`：流量相关数据（设备、流量记录）
- `alert_rules.db`：告警相关数据（规则、历史）

**使用 SQLAlchemy Binds**：
```python
app.config['SQLALCHEMY_BINDS'] = {
    'traffic': 'sqlite:///traffic_data.db',
    'alerts': 'sqlite:///alert_rules.db'
}
```

#### 6.2 数据模型关系

```
users (users.db)
  │
  └─► token (用于API认证)

devices (traffic_data.db)
  │
  ├─► device_traffic (一对多)
  │   └─► device_id (外键)
  │
  └─► alert_rules (可选，device_id可为NULL)
      └─► alert_history (一对多)
          └─► rule_id (外键)
```

#### 6.3 数据索引优化

关键字段建立索引以提高查询性能：

```python
# users表
username = db.Column(db.String(80), unique=True, index=True)
token = db.Column(db.String(64), unique=True, index=True)

# total_traffic表
timestamp = db.Column(db.DateTime, nullable=False, index=True)

# device_traffic表
device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), index=True)
timestamp = db.Column(db.DateTime, nullable=False, index=True)
```

### 7. 配置管理机制

#### 7.1 配置文件结构

使用 INI 格式配置文件，支持三个配置段：

```ini
[bandix]        # OpenWrt连接配置
[api]           # API服务配置
[collector]     # 数据收集配置
```

#### 7.2 配置热重载

**重载机制**：
```python
def reload_app_config():
    # 1. 重新读取配置文件
    bandix_config, api_config = load_config_file()
    
    # 2. 重新初始化监控器实例
    global monitor
    monitor = None  # 下次调用get_monitor()时会重新创建
    
    # 3. 通知数据收集服务重载配置
    reload_collector_config()
```

**动态更新**：
- 数据收集服务在每次循环前重新读取配置
- 支持在不重启服务的情况下修改收集间隔
- 配置修改通过Web界面保存后立即生效

#### 7.3 配置验证

在保存配置前进行验证：

- URL格式验证
- 端口范围验证（1-65535）
- 数值类型验证
- 必填字段检查

### 8. 前端交互机制

#### 8.1 单页面应用（SPA）架构

虽然使用传统HTML页面，但通过JavaScript实现了类似SPA的体验：

- 所有功能标签页都在同一个HTML文件中
- 通过显示/隐藏 `<div>` 实现标签切换
- 无需页面刷新即可切换功能

**标签切换机制**：
```javascript
function switchTab(tabName) {
    // 隐藏所有标签页
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // 显示目标标签页
    document.getElementById(tabName + 'Tab').classList.add('active');
    
    // 初始化对应功能（如果需要）
    if (tabName === 'dashboard') {
        initDashboard();
    }
}
```

#### 8.2 数据可视化实现

**Chart.js 集成**：

1. **图表容器**：使用 `<canvas>` 元素
2. **数据获取**：通过API获取聚合后的数据
3. **图表渲染**：
   ```javascript
   const ctx = document.getElementById('chartCanvas').getContext('2d');
   const chart = new Chart(ctx, {
       type: 'line',  // 或 'bar', 'pie' 等
       data: {
           labels: timeLabels,
           datasets: [{
               label: '下行流量',
               data: downSpeedData,
               borderColor: 'rgb(75, 192, 192)'
           }]
       }
   });
   ```

4. **主题适配**：根据暗色/亮色主题动态调整图表颜色

#### 8.3 数据导出实现

**CSV导出**：
- 前端直接生成CSV字符串
- 使用 `Blob` API创建文件
- 通过 `<a>` 标签的 `download` 属性触发下载

**Excel导出**：
- 使用 SheetJS (xlsx) 库
- 将数据转换为工作簿格式
- 使用 `XLSX.writeFile()` 直接下载

### 9. 性能优化策略

#### 9.1 数据库查询优化

- **索引使用**：关键查询字段建立索引
- **分页查询**：大数据量时使用LIMIT和OFFSET
- **聚合查询**：在数据库层面进行SUM、AVG等聚合操作
- **连接优化**：使用JOIN减少查询次数

#### 9.2 前端性能优化

- **防抖/节流**：搜索输入框使用防抖，避免频繁请求
- **数据缓存**：设备列表等静态数据缓存到内存
- **懒加载**：图表等重型组件按需加载
- **CSS优化**：使用CSS变量支持主题切换，减少重复代码

#### 9.3 并发处理

- **线程安全**：数据库操作使用SQLAlchemy的会话管理
- **锁机制**：关键操作使用数据库事务保证一致性
- **异步处理**：数据收集和告警检查在后台线程执行

### 10. 错误处理与日志

#### 10.1 异常处理策略

**分层错误处理**：
1. **服务层**：捕获业务异常，返回错误信息
2. **API层**：捕获异常，返回标准错误响应
3. **前端**：捕获网络错误，显示友好提示

**错误响应格式**：
```python
{
    "success": False,
    "error": "错误描述",
    "data": None
}
```

#### 10.2 日志记录

- **控制台输出**：开发环境直接输出到控制台
- **时间戳**：所有日志包含时间戳
- **错误追踪**：关键错误使用 `traceback.print_exc()` 记录堆栈

## 📝 开发指南

### 代码结构

- **API 路由**：`app/api/` - 所有 API 端点定义
- **数据模型**：`app/models/` - 数据库模型定义
- **业务逻辑**：`app/services/` - 核心业务逻辑服务
- **前端模板**：`app/templates/` - HTML 模板文件

### 添加新功能

1. **添加新的 API 端点**：
   - 在 `app/api/` 中创建或修改相应的蓝图文件
   - 添加路由处理函数
   - 更新 Swagger 文档注释

2. **添加新的数据模型**：
   - 在 `app/models/` 中定义模型类
   - 继承 `db.Model`
   - 在应用初始化时创建表

3. **添加新的服务**：
   - 在 `app/services/` 中实现服务类或函数
   - 保持单一职责原则

### 代码风格

- 遵循 PEP 8 Python 代码规范
- 使用类型提示（可选）
- 添加适当的文档字符串
- 保持代码简洁和可读性

## 📄 许可证

本项目采用 MIT 许可证。详情请参阅 LICENSE 文件。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送邮件（如果有）

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者！

---

**注意**：本项目为 OpenWrt 流量监控系统，请确保在使用前仔细阅读配置说明和安全建议。
