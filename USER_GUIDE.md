# 用户管理系统使用指南

## 功能概述

用户管理系统为 Bandix Monitor API 提供了完整的用户注册、登录和 Token 管理功能。每个用户拥有独立的 API Token，用于访问监控 API。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python bandix_api.py
```

服务启动后会自动创建 SQLite 数据库 `users.db`，并创建默认管理员账户：
- 用户名：`admin`
- 密码：`admin123`

**注意：首次启动后请及时修改管理员密码！**

### 3. 访问用户中心

在浏览器中访问：`http://localhost:5000/`

## 功能说明

### 用户注册

1. 在用户中心首页点击"立即注册"
2. 输入用户名（至少3个字符）
3. 输入密码（至少6个字符）
4. 点击"注册"按钮
5. 注册成功后，系统会显示您的 API Token

### 用户登录

1. 输入用户名和密码
2. 点击"登录"按钮
3. 登录成功后进入用户中心

### 查看 Token

登录后，在用户中心可以看到：
- 用户名
- API Token
- 创建时间
- Token 使用示例

### 刷新 Token

如果 Token 泄露或需要更新：
1. 点击"刷新 Token"按钮
2. 确认操作
3. 旧的 Token 将立即失效，新的 Token 会显示

### 退出登录

点击"退出登录"按钮即可退出当前会话

## API 使用

### 使用用户 Token 访问 API

注册/登录后，您会获得一个唯一的 API Token。使用该 Token 可以访问所有需要认证的 API 端点。

#### 方式1：使用 Header（推荐）

```bash
curl -H "X-API-Key: YOUR_TOKEN" http://localhost:5000/api/monitor
```

#### 方式2：使用查询参数

```bash
curl http://localhost:5000/api/monitor?api_key=YOUR_TOKEN
```

#### 方式3：使用 Authorization Header

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:5000/api/monitor
```

### Python 示例

```python
import requests

API_URL = "http://localhost:5000/api/monitor"
TOKEN = "your-token-here"

response = requests.get(
    API_URL,
    headers={"X-API-Key": TOKEN}
)

data = response.json()
if data["success"]:
    print(data["data"])
```

### JavaScript 示例

```javascript
const token = 'your-token-here';
fetch('http://localhost:5000/api/monitor', {
  headers: {
    'X-API-Key': token
  }
})
.then(response => response.json())
.then(data => {
  if (data.success) {
    console.log(data.data);
  }
});
```

## 用户管理 API

### 注册用户

**端点：** `POST /api/user/register`

**请求体：**
```json
{
  "username": "myuser",
  "password": "mypassword"
}
```

**响应：**
```json
{
  "success": true,
  "message": "注册成功",
  "data": {
    "username": "myuser",
    "token": "generated-token"
  }
}
```

### 用户登录

**端点：** `POST /api/user/login`

**请求体：**
```json
{
  "username": "myuser",
  "password": "mypassword"
}
```

**响应：**
```json
{
  "success": true,
  "message": "登录成功",
  "data": {
    "username": "myuser",
    "token": "user-token"
  }
}
```

### 获取用户信息

**端点：** `GET /api/user/info`

**需要登录：** 是（通过 Session）

**响应：**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "myuser",
    "token": "user-token",
    "created_at": "2023-12-21T10:00:00",
    "is_active": true
  }
}
```

### 刷新 Token

**端点：** `POST /api/user/token/refresh`

**需要登录：** 是（通过 Session）

**响应：**
```json
{
  "success": true,
  "message": "Token刷新成功",
  "data": {
    "token": "new-token"
  }
}
```

### 退出登录

**端点：** `POST /api/user/logout`

**需要登录：** 是（通过 Session）

**响应：**
```json
{
  "success": true,
  "message": "登出成功"
}
```

## 安全建议

1. **修改默认管理员密码**：首次启动后立即修改管理员密码
2. **使用强密码**：密码至少6个字符，建议使用字母、数字和特殊字符组合
3. **保护 Token**：不要将 Token 提交到代码仓库或公开分享
4. **定期刷新 Token**：如果怀疑 Token 泄露，立即刷新
5. **使用 HTTPS**：生产环境中务必使用 HTTPS 加密通信

## 数据库

系统使用 SQLite 数据库存储用户信息，数据库文件为 `users.db`。

### 数据库结构

- **users** 表
  - id: 用户ID（主键）
  - username: 用户名（唯一）
  - password_hash: 密码哈希
  - token: API Token（唯一）
  - created_at: 创建时间
  - updated_at: 更新时间
  - is_active: 是否激活

### 备份数据库

```bash
# 备份数据库
cp users.db users.db.backup
```

### 重置数据库

如需重置数据库，删除 `users.db` 文件后重启服务即可。

## 故障排查

### 无法登录

- 检查用户名和密码是否正确
- 确认用户账户是否被禁用（is_active=false）
- 查看服务器日志

### Token 无效

- 确认 Token 是否正确复制（无多余空格）
- 检查 Token 是否已刷新（旧 Token 会失效）
- 确认用户账户是否被禁用

### 数据库错误

- 检查 `users.db` 文件权限
- 确认磁盘空间充足
- 查看错误日志

## 版本信息

- 用户管理系统版本：1.0.0
- 支持 Python 3.6+

