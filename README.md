# 优纳特销售网站

## 导入两轮筛选通过的 985/211 高校并补齐体育院校坐标

该批次包含 39 所 985 和 60 所仅 211 高校。它不覆盖既有档案；地址以“城市+学校名”进入高德队列，只有严格同名或名称标注“主校区”的 POI 才能补齐地址和地图 pin。随后同一编码命令会处理现有体育院校和低置信度的四川大学。

```powershell
Set-Location -LiteralPath 'D:\桌面\优纳特销售网站'
& 'C:\Users\alien\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe' compose up -d --build api
& 'C:\Users\alien\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe' compose exec api python -m app.cli.import_verified_985_211_universities
& 'C:\Users\alien\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe' compose exec api python -m app.cli.geocode_pending_sites
```

面向内部管理员的全国目标单位数据库与地图审核平台。首期以 PostgreSQL/PostGIS 保存可追溯目标单位、地点、来源依据、联系人预留字段、商机和已成交项目；FastAPI 提供 `/api/v1` 接口，Next.js 提供审核列表与高德聚合地图。

> 默认项目路径固定为 `D:\桌面\优纳特销售网站`。所有命令从该目录执行。

## 已实现范围

- Docker Compose：PostGIS 16、Redis、FastAPI、Next.js 和 Nginx 网关；数据库不发布到主机端口。
- 首版 Alembic 迁移：`organization`、`organization_site`、`organization_evidence`、`organization_contact`、`opportunity`、`sales_project`、导入批次、重复候选和审核日志。
- 高校/研究院必须有纳入证据；体育高校可标记体育例外；新单位默认“潜在客户 + 待核验”。
- `/`：公司内部授权账号登录后查看全国单位地图和数据洞察；单位数据库仅保留在数据后台，未登录时不挂载业务页面且业务 API 返回 401。
- `/admin/organizations`：管理员维护业务数据和“普通员工 / 管理员”授权账号；支持筛选、核验、高德 `MarkerCluster` 地图及 Excel 导出。

## 首次配置

1. 复制根目录模板为 `.env`（文件已存在时只核对变量，不提交到 Git）。
2. 填写以下变量，值不可写进代码、截图或提交记录：

```env
POSTGRES_DB=unite_map
POSTGRES_USER=unite
POSTGRES_PASSWORD=使用密码管理器生成的随机密码
APP_PORT=33100
CORS_ORIGINS=http://localhost:33100
ADMIN_USERNAME=admin
ADMIN_PASSWORD=至少16位随机密码
APP_ENVIRONMENT=development
ADMIN_COOKIE_SECURE=false
AMAP_WEB_KEY=高德Web端JSAPI Key
AMAP_SECURITY_JS_CODE=高德安全密钥
```

`APP_PORT=33100` 用于避开本机 Next.js 开发端口及 Windows 保留端口段。`CORS_ORIGINS` 必须与浏览器实际入口完全一致，正式环境填写完整 HTTPS 域名。高德安全密钥仅进入 Nginx 服务端代理，浏览器代码不会读取它。本地 HTTP 保持 `APP_ENVIRONMENT=development` 与 `ADMIN_COOKIE_SECURE=false`；正式 HTTPS 环境改为 `APP_ENVIRONMENT=production` 和 `ADMIN_COOKIE_SECURE=true`，否则 API 会拒绝启动。连接池、查询超时和登录锁定的生产参数见 `.env.example`，默认值适合单 API 实例。

## 启动与检查

```powershell
Set-Location -LiteralPath 'D:\桌面\优纳特销售网站'
docker compose build
docker compose up -d
docker compose ps
```

首次 API 容器启动时自动执行 `alembic upgrade head`。打开 `http://localhost:3100/`，先使用 `.env` 中配置的管理员账号登录；该账号会作为首个管理员，可在后台“授权账号”页继续添加普通员工或管理员。

健康检查分三层：兼容入口 `/api/v1/health`、无外部依赖的存活探针 `/api/v1/health/live`、同时检查 PostgreSQL 与 Redis 的生产就绪探针 `/api/v1/health/ready`。Compose 使用就绪探针控制依赖启动。

升级到 `20260820_0018` 会清空旧管理员会话以建立 CSRF 哈希，管理员需重新登录一次。此后所有写请求都同时校验 HTTP-only 会话 Cookie 和 CSRF 请求头，连续失败登录会触发临时账户锁，Nginx 还会对登录入口按 IP 限速。

### 导出当前筛选的单位

登录 `http://localhost:3100/admin/organizations` 后，先设置名称、单位类型、审核状态、省市区、地址编码状态或体育例外等筛选条件，再点击右上角“导出当前筛选”。浏览器会下载 Excel，其中包含单位基本信息、主地址、经纬度/编码状态、纳入理由和所有来源证据；联系人手机号、邮箱等受保护字段不会导出。

### 导入首批 C9 高校

该命令会创建一个导入批次，将北京大学、清华大学、复旦大学、上海交通大学、南京大学、浙江大学、中国科学技术大学、哈尔滨工业大学和西安交通大学写入数据库。每条均附一条学校官方化学/材料相关院系证据；不会覆盖已存在单位。当前未配置高德 Web 服务地理编码 Key 时，地点状态为“待编码”，因此不会显示地图 pin。

```powershell
Set-Location -LiteralPath 'D:\桌面\优纳特销售网站'
& 'C:\Users\alien\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe' compose up -d --build api
& 'C:\Users\alien\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe' compose exec api python -m app.cli.import_c9_universities
```

### 导入教育部全国普通高校筛选底表

该命令通过教育部官方全国高校查询接口读取 2026 年普通高校目录，写入 `import_batch` 和 `import_row`，而不是将 2,952 所高校不加筛选地作为正式客户。每条都会保留学校标识码、主管部门、所在地、办学层次和官方来源；体育高校进入“体育例外待取证”，其他高校进入“待生环化材专业证据”。只有补齐高校官方的生物、环境、化学、材料相关院系/专业/科研证据后，才可进入 `organization` 并参与地址编码与地图 pin。

所有未来官方名单导入共用“低并发 + 有限重试 + 全量校验后提交”的安全边界。默认同时请求 4 页；如某个官方站点限流更严，可在根 `.env` 将 `OFFICIAL_IMPORT_MAX_PARALLEL_REQUESTS` 调低至 `1`，上限为 `8`。`OFFICIAL_IMPORT_MAX_REQUEST_ATTEMPTS` 和 `OFFICIAL_IMPORT_REQUEST_TIMEOUT_SECONDS` 也可按来源稳定性调整。

### 导入已逐校核验的高校并地理编码

`import_verified_universities_batch_01` 仅处理已人工核验官网院系/专业证据的高校。它会创建正式单位、回写同名教育部底表行的处理状态，并将校址放入高德待编码队列；随后运行编码命令，只有高可信度结果才生成地图 pin。

```powershell
Set-Location -LiteralPath 'D:\桌面\优纳特销售网站'
& 'C:\Users\alien\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe' compose exec api python -m app.cli.import_verified_universities_batch_01
& 'C:\Users\alien\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe' compose exec api python -m app.cli.geocode_pending_sites
```

```powershell
Set-Location -LiteralPath 'D:\桌面\优纳特销售网站'
& 'C:\Users\alien\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe' compose up -d --build api
& 'C:\Users\alien\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe' compose exec api python -m app.cli.import_moe_university_directory
```

停止服务但保留数据：

```powershell
Set-Location -LiteralPath 'D:\桌面\优纳特销售网站'
& 'C:\Users\alien\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe' compose down
```

不要在不需要清空数据时使用 `docker compose down -v`，该命令会删除 PostgreSQL 数据卷。

### 为待编码单位创建地图 pin

根目录 `.env` 的 `AMAP_REST_API_KEY` 必须是高德“Web 服务”类型 Key；它只传入 FastAPI 容器，绝不写入 Next.js。更新 API 后执行：

```powershell
Set-Location -LiteralPath 'D:\桌面\优纳特销售网站'
& 'C:\Users\alien\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe' compose up -d --build api
& 'C:\Users\alien\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe' compose exec api python -m app.cli.geocode_pending_sites
```

命令仅将门牌号、兴趣点等可靠匹配写入数据库；若地址只匹配到行政区，则只接受同单位名称（或同校区）且门牌号一致的高德 POI 作为二次校验。成功记录会立即由 `/admin/organizations` 的现有 `AMap.MarkerCluster` 聚合展示，低可信度或无结果记录保留给人工补地址。

## 本地非容器验证

```powershell
Set-Location -LiteralPath 'D:\桌面\优纳特销售网站'
$env:PYTHONPATH = 'backend'
& '.\.venv\Scripts\python.exe' -B -m pytest backend\tests -q
Push-Location backend
& '..\.venv\Scripts\python.exe' -B -m alembic upgrade head --sql
Pop-Location
```

## 数据导入原则

不把真实单位、联系人或高德密钥提交到仓库。后续官方名单导入必须创建 `import_batch`，保留原始来源 URL/采集日期/证据；教育部高校底表不等同正式目标单位，必须完成专业/体育例外取证后才可创建 `organization`。地址编码失败的记录保留在“待补地址”，不生成地图 pin。对两万条规模新增可空字段、关联表或索引都采用 Alembic 迁移；新增必填字段遵循“先允许为空 → 补齐旧数据 → 再加约束”。
