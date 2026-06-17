# 成都景点分布地图 · Redis GEO 原型系统

这是一个基于 **Flask + Redis GEO + 高德地图 JS API** 的地标管理系统，适合作为软件工程课程期末项目展示。系统以成都景点为示例数据，支持地图可视化、地标管理、附近搜索、距离计算、用户登录注册、用户收藏、统计看板以及 JSON 数据导入导出。

## 功能特性

- 地图展示成都景点 Marker
- 地标新增、查询、编辑、删除
- 点击地图自动拾取经纬度
- 分类筛选与关键词搜索
- Redis GEO 附近搜索
- Redis GEO 两点距离计算
- JSON 导入 / 导出
- 一键恢复成都示例数据
- 用户注册、登录、退出登录
- 用户角色与接口权限控制
- 登录用户收藏 / 取消收藏地标
- “只看我的收藏”筛选
- 数据统计看板：地标数、分类数、用户数、Redis 状态
- 自动化 API 测试脚本

## 技术栈

| 层次 | 技术 |
| --- | --- |
| 后端 | Python、Flask |
| 数据库 / 缓存 | Redis、Redis GEO、Redis Hash、Redis Set |
| 前端 | HTML、CSS、原生 JavaScript |
| 地图 | 高德地图 JS API |
| 测试 | Flask test client |
| 部署 | Gunicorn、Procfile |

## Redis 数据结构设计

```text
landmark:geo                       GEO    保存地标经纬度
landmark:ids                       Set    保存全部地标 ID
landmark:detail:<landmark_id>      Hash   保存地标详情

user:ids                           Set    保存全部用户名
user:detail:<username>             Hash   保存用户信息和密码哈希
user:favorites:<username>          Set    保存用户收藏的地标 ID
```

## 主要接口

### 地标接口

```text
GET    /api/landmarks
GET    /api/landmarks/<id>
POST   /api/landmarks
PUT    /api/landmarks/<id>
DELETE /api/landmarks/<id>
GET    /api/landmarks/nearby
GET    /api/landmarks/distance
GET    /api/landmarks/export
POST   /api/landmarks/import
POST   /api/landmarks/reset-seed
```

### 用户接口

```text
POST   /api/users/register
POST   /api/users/login
POST   /api/users/logout
GET    /api/users/me
GET    /api/users
GET    /api/users/<username>
```

### 收藏接口

```text
GET    /api/users/me/favorites
POST   /api/users/me/favorites/<landmark_id>
DELETE /api/users/me/favorites/<landmark_id>
```

### 统计接口

```text
GET /api/stats
```

## 本地运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
FLASK_SECRET_KEY=please-change-me
ADMIN_USERNAMES=admin
AMAP_KEY=你的高德地图Key
AMAP_SECURITY_CODE=你的高德安全密钥
```

如果使用云 Redis，也可以配置：

```env
REDIS_URL=redis://用户名:密码@主机:端口/0
```

### 管理员账号说明

系统通过环境变量 `ADMIN_USERNAMES` 配置管理员用户名，多个用户名用英文逗号分隔：

```env
ADMIN_USERNAMES=admin,teacher
```

注册用户名命中该配置时，该用户会自动拥有 `admin` 角色；其他注册用户默认为 `user` 角色。

## 接口权限说明

| 接口 | 权限 |
| --- | --- |
| `GET /api/landmarks`、`GET /api/landmarks/<id>` | 公开访问 |
| `GET /api/landmarks/nearby`、`GET /api/landmarks/distance` | 公开访问 |
| `GET /api/landmarks/export` | 公开访问 |
| `POST /api/landmarks` | 登录用户 |
| `PUT /api/landmarks/<id>` | 登录用户 |
| `DELETE /api/landmarks/<id>` | 管理员 |
| `POST /api/landmarks/import` | 管理员 |
| `POST /api/landmarks/reset-seed` | 管理员 |
| `GET /api/users/me` | 公开访问，返回当前登录状态 |
| `GET /api/users/me/favorites`、`POST/DELETE /api/users/me/favorites/<id>` | 登录用户 |
| `GET /api/users` | 管理员 |
| `GET /api/users/<username>` | 用户本人或管理员 |

未登录访问受保护接口会返回 `401`；登录但权限不足会返回 `403`。

### 3. 启动 Redis

确保本地或远程 Redis 可连接。

### 4. 初始化示例数据

```bash
python seed_data.py
```

### 5. 启动应用

```bash
python app.py
```

浏览器访问：

```text
http://localhost:5000
```

## 运行测试

```bash
python test_api.py
```

测试内容包括：

- 首页和健康检查
- 用户注册、登录、退出
- 登录 / 管理员接口权限控制
- 地标 CRUD
- 附近搜索和距离计算
- JSON 导入导出
- 统计接口
- 用户收藏接口

## 项目亮点

1. **Redis GEO 实践**：使用 `GEOADD`、`GEOSEARCH`、`GEODIST` 实现地理位置搜索和距离计算。
2. **多数据结构组合**：使用 GEO、Hash、Set 分别管理坐标、详情、索引和收藏关系。
3. **前后端完整闭环**：接口、页面、地图交互、错误提示和自动化测试均已覆盖。
4. **用户体系落地**：用户登录后可收藏地标，并支持只查看个人收藏。
5. **权限控制闭环**：区分游客、普通用户和管理员，对新增、编辑、删除、导入、恢复示例数据等操作设置权限边界。
6. **工程化展示**：包含测试脚本、环境变量配置、部署入口和项目文档。

## 后续可扩展方向

- 地标评分和评论
- 多点路线规划和总距离计算
- 操作日志 / 审计记录
- Docker Compose 一键启动 Flask + Redis
- 使用 ECharts 展示分类统计图表
