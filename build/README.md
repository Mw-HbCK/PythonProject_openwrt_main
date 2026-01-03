# 二进制打包说明

本目录包含将 Bandix Monitor 编译为二进制文件的所有配置和脚本。

## 📁 文件说明

- `pyinstaller.spec` - PyInstaller 详细配置文件
- `build_binary.sh` - 完整打包脚本（推荐）
- `build_binary_simple.sh` - 简化版打包脚本
- `BINARY_DEPLOY.md` - 二进制部署文档

## 🚀 快速开始

### 方法一：使用完整脚本（推荐）

```bash
chmod +x build/build_binary.sh
./build/build_binary.sh
```

### 方法二：使用简化脚本

```bash
chmod +x build/build_binary_simple.sh
./build/build_binary_simple.sh
```

### 方法三：手动打包

```bash
# 安装 PyInstaller
pip install pyinstaller

# 使用 spec 文件打包
pyinstaller build/pyinstaller.spec
```

## 📦 打包要求

### 系统要求

- Ubuntu 24.04 或兼容系统
- Python 3.10+
- 足够的磁盘空间（至少 500MB）

### Python 依赖

所有依赖已在 `requirements.txt` 中定义，打包脚本会自动安装。

## 🔧 自定义配置

### 修改打包选项

编辑 `pyinstaller.spec` 文件：

```python
# 修改可执行文件名
name='bandix-monitor'

# 修改为单文件模式（已启用）
onefile=True

# 添加图标
icon='path/to/icon.ico'
```

### 添加额外文件

在 `pyinstaller.spec` 的 `datas` 部分添加：

```python
datas=[
    ('path/to/file', 'destination/path'),
]
```

## 📋 打包后的文件结构

```
build/dist/bandix-monitor/
├── bandix-monitor          # 可执行文件
├── start.sh                # 启动脚本
├── bandix-monitor.service   # systemd 服务文件
├── app/
│   └── config/
│       └── bandix_config.ini
└── README.txt
```

## 🚢 部署

详细部署说明请参考 `BINARY_DEPLOY.md`

## ⚠️ 注意事项

1. **文件大小**：打包后的二进制文件可能较大（100-200MB）
2. **系统兼容性**：需要在相同架构的系统上运行
3. **依赖库**：目标系统需要安装必要的系统库
4. **配置文件**：首次运行前必须配置

## 🐛 常见问题

### 打包失败

- 检查 Python 版本
- 确保所有依赖已安装
- 查看 PyInstaller 错误信息

### 运行时错误

- 检查系统库是否安装
- 查看应用日志
- 验证配置文件路径

### 文件太大

- 使用 `--exclude-module` 排除不需要的模块
- 使用 `--strip` 选项（Linux）
- 考虑使用 `--onedir` 模式而非 `--onefile`

## 📚 更多信息

- [PyInstaller 文档](https://pyinstaller.org/)
- [部署文档](../DEPLOY_UBUNTU.md)
- [二进制部署文档](BINARY_DEPLOY.md)

