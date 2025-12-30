# 项目文件结构说明

由于文件移动操作遇到一些问题，以下是推荐的项目文件组织结构：

## 推荐的项目结构

```
bandix-monitor/
├── app/                      # 应用主目录
│   ├── __init__.py
│   ├── bandix_api.py        # 主应用入口
│   ├── api/                 # API 路由
│   │   ├── __init__.py
│   │   ├── user_api.py      # 用户管理API
│   │   └── database_api.py  # 数据查询API
│   ├── models/              # 数据模型
│   │   ├── __init__.py
│   │   ├── user_models.py   # 用户模型
│   │   └── database_models.py  # 流量数据模型
│   ├── services/            # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── bandix_monitor.py  # OpenWrt通信服务
│   │   └── data_collector.py  # 数据收集服务
│   ├── templates/           # HTML模板
│   │   ├── index.html       # 用户中心页面
│   │   └── data_query.html  # 数据查询页面
│   └── config/              # 配置文件
│       └── bandix_config.ini
├── docs/                    # 文档目录
│   ├── API_README.md        # API使用文档
│   └── USER_GUIDE.md        # 用户指南
├── requirements.txt         # Python依赖
├── run.py                   # 启动脚本
├── README.md               # 项目说明
└── PROJECT_STRUCTURE.md    # 本文档
```

## 当前文件状态

文件可能还没有完全移动到正确的位置。请手动按照上述结构组织文件。

## 需要更新的导入语句

文件移动到新位置后，需要更新以下导入语句：

### app/bandix_api.py
```python
from services.bandix_monitor import BandixMonitor
from models.user_models import db as user_db, User, init_db as init_user_db
from api.user_api import user_bp
from api.database_api import db_bp
from models.database_models import db as traffic_db, init_database_tables
from services.data_collector import start_collector
```

### app/api/user_api.py
```python
from models.user_models import db, User
```

### app/api/database_api.py
```python
from models.database_models import db, Device, TotalTraffic, DeviceTraffic
```

### app/services/data_collector.py
```python
from models.database_models import db, Device, TotalTraffic, DeviceTraffic, init_database_tables
```

## 注意事项

1. 所有 `app/` 下的子目录都需要 `__init__.py` 文件
2. Flask 应用的 `template_folder` 需要设置为 `'templates'`
3. 配置文件路径需要使用 `os.path.join` 动态生成

