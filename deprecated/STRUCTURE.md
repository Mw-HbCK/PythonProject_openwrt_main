# 项目文件结构

## 当前项目结构

```
bandix-monitor/
├── app/                          # 应用主目录
│   ├── __init__.py
│   ├── bandix_api.py            # 主应用入口
│   ├── api/                     # API路由模块
│   │   ├── __init__.py
│   │   ├── user_api.py          # 用户管理API（注册、登录、Token管理）
│   │   └── database_api.py      # 数据查询API（流量数据查询）
│   ├── models/                  # 数据模型模块
│   │   ├── __init__.py
│   │   ├── user_models.py       # 用户数据模型（users.db）
│   │   └── database_models.py   # 流量数据模型（traffic_data.db）
│   ├── services/                # 业务逻辑服务模块
│   │   ├── __init__.py
│   │   ├── bandix_monitor.py    # OpenWrt设备通信服务
│   │   └── data_collector.py    # 数据收集服务（定时存储）
│   ├── templates/               # HTML模板
│   │   ├── index.html           # 用户中心页面
│   │   └── data_query.html      # 数据查询页面
│   └── config/                  # 配置文件
│       └── bandix_config.ini    # 主配置文件
├── docs/                        # 文档目录
│   ├── API_README.md            # API使用文档
│   └── USER_GUIDE.md            # 用户指南
├── requirements.txt             # Python依赖包
├── run.py                       # 启动脚本
├── README.md                    # 项目说明
└── STRUCTURE.md                 # 本文件
```

## 模块说明

### 1. app/bandix_api.py
主应用入口文件，负责：
- Flask应用初始化
- 数据库配置
- 蓝图注册
- 路由定义
- 应用启动

### 2. app/api/
API路由模块，包含：
- **user_api.py**: 用户管理相关API
  - `/api/user/register` - 用户注册
  - `/api/user/login` - 用户登录
  - `/api/user/logout` - 退出登录
  - `/api/user/info` - 获取用户信息
  - `/api/user/token/refresh` - 刷新Token

- **database_api.py**: 数据查询API
  - `/api/database/devices` - 获取设备列表
  - `/api/database/total-traffic` - 获取全网流量数据
  - `/api/database/device-traffic/<id>` - 获取设备流量数据
  - `/api/database/stats` - 获取统计信息

### 3. app/models/
数据模型模块，定义数据库表结构：
- **user_models.py**: 用户相关表（users表）
- **database_models.py**: 流量数据相关表（devices, total_traffic, device_traffic表）

### 4. app/services/
业务逻辑服务模块：
- **bandix_monitor.py**: 与OpenWrt设备通信，获取实时流量数据
- **data_collector.py**: 定时收集数据并存储到数据库（每秒一次）

### 5. app/templates/
前端HTML模板：
- **index.html**: 用户中心页面（登录、注册、Token管理）
- **data_query.html**: 数据查询页面（历史数据查询）

### 6. app/config/
配置文件目录：
- **bandix_config.ini**: 主配置文件（设备连接信息、API配置等）

## 数据库文件

- `users.db` - 用户和Token信息（自动创建）
- `traffic_data.db` - 流量历史数据（自动创建）

## 启动方式

### 方式1：使用启动脚本（推荐）
```bash
python run.py
```

### 方式2：直接运行主文件
```bash
python app/bandix_api.py
```

## 文件分类总结

| 类型 | 文件/目录 | 说明 |
|------|----------|------|
| **主应用** | `app/bandix_api.py` | Flask应用入口 |
| **API路由** | `app/api/` | 所有API端点 |
| **数据模型** | `app/models/` | 数据库表定义 |
| **业务服务** | `app/services/` | 核心业务逻辑 |
| **前端模板** | `app/templates/` | HTML页面 |
| **配置文件** | `app/config/` | 配置文件 |
| **文档** | `docs/` | 项目文档 |
| **启动脚本** | `run.py` | 启动入口 |

