# 项目架构与文件职责

## 2026-08 全栈保守优化与安全加固

- 单位筛选分页不再连接地点表后直接 `offset/limit`，统一改为关联 `EXISTS` 条件；多地点单位只占一个分页槽位，省、市、区及编码状态仍要求命中同一地点。公开目录使用独立轻量查询，只预加载公开地点并在 SQL 中聚合证据数量，不再读取联系人、商机、成交项目或证据正文。
- 管理端手工新增/修改地点与自动地理编码复用同一 GCJ-02→WGS84 转换入口：`longitude/latitude` 继续供 AMap 显示，PostGIS `location` 始终按 SRID 4326 写入。单位改名也执行排除自身后的标准化同名检查。
- Excel 导出对所有字符串统一防公式注入处理；以 `= + - @` 或控制字符开头的内容以纯文本保存。离线测试新增导出公式与管理员坐标转换回归，后端当前共 99 条测试。
- 公开单位库和管理员工作台对搜索做 250ms 防抖，在筛选/页容量事件内原子回到第一页，并取消过期请求；列表、层级选项和地图点位使用独立错误边界，旧响应不会覆盖新筛选。FastAPI 的 Pydantic 422 数组会被格式化为字段级可读消息。
- `AdminOrganizationMap` 使用明确的最小 AMap 类型边界；Loader 失败不会永久缓存，SDK 加载具备两次有限超时，卸载会取消异步初始化。MarkerCluster 回调通过最新数据 ref 回查点位并兼容 `extData`，筛选变化后不会继续打开旧单位。
- 首页移除约 500 行已无入口的旧 SVG 项目地图/关系网实现；保留当前 AMap 点位图、省级热力图和数据洞察。GSAP 入场仅动画 `transform/opacity`，移除大面积 `filter: blur()` 重绘，并继续尊重 `prefers-reduced-motion`。
- 前端生产依赖移除 13 个源码零引用包；Next.js / `eslint-config-next` 升至 16.3.0，并将审计收敛为 0 个已知漏洞。生产镜像以 `npm ci` 复现依赖，使用 Next standalone 输出且以非 root `node` 用户运行，不再复制完整开发依赖。

## 2026-08 行业单位地图与单位数据库数据接入

- `localhost:3100/` 是匿名可读主站，使用 `/api/v1/public/organizations`、`/filters` 与 `/province-summaries`；公开列表 DTO 只包含页面正在显示的字段，不返回详细地址、坐标、备注、证据链接或摘录。省级汇总只返回单位总量、单位类型和客户状态计数。
- `localhost:3100/admin/organizations` 与主站同属一个 Next.js 部署；顶部“管理员入口”链接至该路由，管理员工作台页头只保留“全国目标单位”主标题，顶部距离压缩至约 20px，并继续调用受 Cookie 会话保护的 `/api/v1/organizations/*`。工作台默认不挂载地图且列表占满内容区；“显示地图/关闭地图”在列表标题栏切换双栏视图，地图展开时保留当前页及每页容量，只展示当前批次最前面的 10 条单位；“仅已核验地图 pin”只在地图标题栏出现且不改变列表或导出条件。地图展开时隐藏列表操作列，五个信息列自适应填满列表卡且不产生横向滚动；地图关闭后恢复修改与删除操作。
- 管理员单位列表保留详情抽屉并新增独立“修改/删除”操作列；地图关闭时分页栏支持每页 10、25、50、75、100 条并默认 10 条，切换容量后回到第一页；展开地图会暂时隐藏容量选择器，关闭地图后仍停留在原页并恢复原容量。“添加单位”橙色按钮在地图开关旁始终可见，复用居中修改表单的分区与字段；新增时名称、单位类型、省份和城市必填，可选录入联系人、成交项目、商机与公开证据。前后端集中保留必填配置入口，标准化同名单位返回重复提醒，整套主档、主地点和关联记录在单一事务写入。修改对话框按“基本信息与合作进展、联系人、成交项目、商机、主地点与定位”分区；联系人、成交项目和商机按一对多记录新增、修改或移除，并与单位主档在同一事务保存。取消不会提交草稿；新增、保存、审核和删除成功后在页面中下部悬浮提示 2 秒且不占布局；删除对话框固定在视口中央，明确展示级联影响并在二次确认后调用 `DELETE /api/v1/organizations/{id}`，服务端保留删除审计。
- `organization` 通过 `20260810_0004` 增加最近跟进时间、最近跟进内容、跟进负责人、合作意向和合作等级。匿名主站只读取最近跟进时间/内容及合作意向/等级；跟进负责人、联系人电话邮箱、管理员备注等受保护字段不进入公开 DTO。
- `backend/app/routers/organizations.py` 的 `/organizations/filters` 按已选省、市返回完整的 `cities`、`districts`；`/organizations/map-points` 继续供管理员点位地图使用；公开 `/public/organizations/province-summaries` 按主地点聚合省级总量、单位类型和客户状态，不暴露单位明细或坐标。
- `frontend/next.config.ts` 在本地开发把同源 `/api/v1/*` 代理到 `BACKEND_API_ORIGIN`（默认 `http://localhost:8000`）；容器部署仍由 Nginx 网关代理，因此管理员 cookie 不需要跨域传递。
- `frontend/src/app/page.tsx` 的主导航保持“全国单位地图”，首页默认显示原 AMap 点位聚合地图；右侧第一、第二个标签分别切换“全国单位地图”和“全国单位热力地图”。点位视图保留省、市、区、单位类型和客户状态筛选，热力视图复用 `home-organization-heatmap.tsx` 的五档多选与省份统计弹层，两种视图状态独立保留。
- `home-organization-heatmap.tsx` 消费省级聚合 API，以极低 1–9、低 10–19、中 20–29、高 30–39、极高 40+ 五档橙红色展示；左侧档位筛选收进保留多选能力的下拉面板，地图左下角缩放控件上方独立显示不含数量范围的五色色阶图例。点击省份后显示置顶统计弹层，地图支持以当前完整视图为最小值的放大、缩小和默认复位。销售常驻点默认关闭；经销商、代理商、合作伙伴覆盖层也默认关闭并可独立或组合显示，分别使用青绿、紫色、带深色对比描边的白色虚线圈，合作等级下拉可筛选一级、二级、三级。所有覆盖层复用同一套 MapSVG 投影与公里半径换算。
- `sales_office_location` 独立保存销售常驻点名称、城市、地址、GCJ-02 坐标、覆盖半径与启用状态；`20260810_0002` 迁移写入杭州、北京、天津、沈阳、成都、广州、武汉、南京、西安九条明确标记的演示数据。主站只读取启用点，受管理员会话保护的查询与修改 API 可维护全部字段。
- `channel_partner_location` 保存渠道名称、类型、地址、可空业务坐标、演示定位坐标、可空授权区域、覆盖半径、可空产品线、合作等级、合同、备注与启用状态；`20260810_0003` 迁移写入三类各 6 条、合计 18 条省会城市演示数据。业务经纬度保持空值，地图暂用独立演示坐标；以后录入业务经纬度后公开地图 API 自动优先使用业务坐标。匿名接口只返回绘图必要字段，不公开合同、备注、产品线或业务坐标。
- `frontend/src/components/home-organization-database.tsx` 在“类型 / 行业”右侧以主地点展示“省市区”，并新增默认空白的“最近跟进”列；七列紧凑栅格排列商业与联系信息，数据列左侧缩进依次为 4、5、5、6、13、13、13px。
- `backend/tests/test_api_contracts.py` 覆盖筛选接口的成功层级结果、超长地点参数校验、未认证访问及匿名省级热力聚合合同。

## 2026-08 已核验 985/211 高校与主校区编码

- `backend/app/cli/import_verified_985_211_universities.py` 是 39 所 985 与 60 所仅 211 高校的可重复执行导入入口：以教育部官方名单为底表，保留两轮筛选结论与官网复核入口；已有档案只会记录为重复候选，不会被覆盖。
- `backend/app/services/geocoding.py` 对“城市+单位名”的历史粗地址新增严格同名主 POI 策略：优先同名或名称明确标注“主校区”的高德 POI；仅在不存在前者时回退到同名且非附属机构的学校校区，补写地址和行政区后再创建 GCJ-02/ WGS84 点位。该策略用于 985/211 主校区、全部体育院校及四川大学低置信度点位。
- 地理编码外部请求单次最多等待五秒；超时记录保持“待编码”，由后续批次或人工补地址处理，绝不以省市中心坐标替代。
- 暂缓的外部请求会更新尝试时间并在待编码队列中后移，避免单个高德慢响应阻塞后续学校；已成功或失败的单条记录仍各自独立提交。
- `backend/tests/test_verified_985_211_universities.py` 与 `backend/tests/test_geocoding.py` 分别覆盖 39+60 名单边界和粗地址 POI 约束；两者均为离线测试，不请求高德或读取真实 Key。

本文件描述当前仓库真实存在的项目结构；规划中的后端与数据库不会被当作已实现功能。项目根目录固定为 `D:\桌面\优纳特销售网站`。

```text
优纳特销售网站/
├─ frontend/                 Next.js 仪表盘、高德地图测试页与单位审核后台
├─ backend/                  FastAPI、Alembic、PostGIS ORM 与单位审核 API
├─ infra/nginx/              同源网关与高德安全服务代理模板
├─ docker-compose.yml        本地全栈容器编排（PostGIS、Redis、API、Web、Nginx）
├─ docs/                     项目说明与需求文档
├─ .venv/                    本地 Python 虚拟环境，禁止提交
├─ AGENTS.md                 面向协作开发者与 AI 的全局工作规范
├─ PRODUCT.md                产品目标、用户与视觉原则
└─ .gitignore                根目录忽略规则（含各层级 ui-check 浏览器截图与本地日志）
```

## 前端：`frontend/`

Next.js 16.3 App Router 应用。当前仪表盘使用 TypeScript、React、GSAP、`@svg-maps/china` 和 Tailwind/PostCSS；高德地图在首页默认点位视图和管理员按需地图中加载。

| 路径 | 作用 |
| --- | --- |
| `src/app/page.tsx` | 主仪表盘页面；首页保持三栏地图骨架，默认组合公开点位 API 与 `AdminOrganizationMap`，右侧标签可切换到省级热力组件；省级热力、销售常驻点及渠道覆盖点分别请求并取消过期请求，任一辅助网络失败不遮断主图，第三个主导航入口仍为单位数据库。已移除无入口的旧 SVG 项目地图与关系网实现。 |
| `src/app/layout.tsx` | App Router 根布局；加载全局样式、设置中文语言和页面元数据。 |
| `src/app/globals.css` | 全站设计令牌、仪表盘布局、响应式断点及动效样式。 |
| `src/app/amap-service/[...path]/route.ts` | 高德 REST 服务代理；在服务端附加安全密钥，不向浏览器暴露密钥。 |
| `src/components/home-organization-database.tsx` | 主页“单位数据库”面板；复用公开单位列表与筛选 API，以橙蓝风格展示安全字段。搜索请求防抖且列表/层级选项分离取消，筛选与页容量原子回到第一页。省、市、区联动保持未选省禁用市、未选市禁用区；默认每页 8 条固定视窗，15/25/50/100 条时页面自然展开。 |
| `src/components/home-organization-heatmap.tsx` | 首页省级单位热力组件；集中维护五档阈值和橙红色阶，以下拉面板保留档位多选，并在左下缩放控件上方呈现紧凑五色色阶；销售网络及经销商、代理商、合作伙伴四类可选覆盖层共用底图投影和半径换算，三类渠道支持独立多选及合作等级筛选。 |
| `src/components/amap-national-test.tsx` | 高德 JS API 全国省级地图实验组件，包含生命周期清理、失败超时和重试状态；当前未绑定主页导航入口。 |
| `src/app/admin/organizations/page.tsx` | `/admin/organizations` 审核后台入口；组合受认证保护的单位工作台。 |
| `src/components/admin-organization-workspace.tsx` | 管理员登录、列表筛选、防抖搜索、可选每页 10/25/50/75/100 条的分页、详情抽屉、核验与导出；过期工作区请求会取消，列表与地图辅助错误隔离。默认全宽列表，地图打开时固定按 10 条查询当前页；地图开关旁始终显示橙色“添加单位”，复用居中档案表单并要求名称、类型、省、市。 |
| `src/components/admin-organization-map.tsx` | 高德 JSAPI 地图组件；由单位审核后台和首页复用。使用完整同源 `serviceHost` 加载安全模式 JSAPI，以 `AMap.MarkerCluster` 聚合；Loader 与 SDK 具备失败恢复、有限超时及卸载清理，Marker 回调通过最新 ref/`extData` 读取当前点位并转义名称。 |
| `src/lib/api.ts` | FastAPI `/api/v1` 请求、同源 cookie、取消信号、字符串/422 数组错误格式化、公开/管理员响应类型及筛选参数工具。 |
| `src/app/favicon.ico` | 浏览器标签页图标。 |
| `public/brand/unite-logo.png` | 顶栏使用的优纳特品牌标识。 |
| `public/file.svg`、`globe.svg`、`next.svg`、`vercel.svg`、`window.svg` | create-next-app 遗留的通用 SVG 素材；当前页面未引用，可在确认无用后另行清理。 |
| `next.config.ts` | Next.js 配置；把 `/_AMapService/*` 重写到内部代理路由。 |
| `Dockerfile` / `.dockerignore` | Next.js 生产镜像；依赖阶段使用 `npm ci`，构建 standalone 输出并编译公开高德 Web Key；运行阶段只复制 standalone/static/public 且使用非 root `node` 用户。 |
| `eslint.config.mjs` | ESLint 的 Next.js Core Web Vitals 与 TypeScript 校验配置。 |
| `postcss.config.mjs` | Tailwind CSS 的 PostCSS 插件配置。 |
| `tsconfig.json` | TypeScript 严格模式、模块解析和 `@/*` 源码别名配置。 |
| `next-env.d.ts` | Next.js 自动生成的类型声明；不应手工编辑。 |
| `package.json` / `package-lock.json` | 前端最小生产依赖与锁定版本；零引用的表单、图表、地图和工具包已移除，锁文件由 npm 生成。 |
| `.env.example` | 不含密钥的高德环境变量模板。 |
| `.env.local` | 仅本机使用的高德密钥配置，已被 Git 忽略，禁止提交或记录具体值。 |
| `.gitignore` | 前端目录的依赖、构建产物、环境变量和本地调试文件忽略规则。 |
| `AGENTS.md` | Next.js 版本差异提醒；前端工作还需同时遵守根目录 `AGENTS.md`。 |
| `CLAUDE.md` | 当前为空的工具占位文件，未承载项目逻辑。 |
| `README.md` | create-next-app 初始说明，尚待替换为本项目的启动与部署说明。 |
| `ui-check/` | 本地浏览器检查产生的截图目录，不属于运行时代码或发布素材。 |
| `.next/`、`node_modules/`、`tsconfig.tsbuildinfo`、`debug.log` | 构建、依赖、缓存或调试产物，均不应提交。 |

## 后端：`backend/`

根目录 `.venv` 已具备 FastAPI、SQLAlchemy、Alembic、PostgreSQL 驱动、GeoAlchemy2、OpenPyXL 与 Redis 依赖。后端已实现 SQLAlchemy/PostGIS ORM、版本化 FastAPI API、服务端管理员会话与首版 Alembic 迁移；GeoAlchemy2 保存可靠坐标点，OpenPyXL 和 Redis 为后续官方名单导入与地理编码队列预留。根目录 `.env.example` 是 Docker Compose、PostgreSQL、高德服务端代理与首个管理员账号的无密钥模板；实际 `.env` 仅在本机保存。

| 路径 | 作用 |
| --- | --- |
| `app/config.py` | Pydantic Settings 配置入口；安全构造 PostgreSQL 连接并从根 `.env`/容器环境读取变量。 |
| `app/database.py` | SQLAlchemy 引擎、会话依赖与 ORM 基类。 |
| `app/models.py` | 单位、地点、销售常驻点、渠道合作点、来源证据、导入批次、重复候选、联系人、商机、成交项目、审计与会话的 PostGIS ORM 模型；单位主档包含最近跟进、负责人、合作意向与合作等级，业务枚举按中文数据库标签读写。 |
| `app/schemas.py` | API 输入/输出验证；管理员新增单位要求名称、类型、主地点省市并拒绝携带既有子记录 ID；另含高校与研究院证据、体育例外、不纳入理由、省级单位聚合、单位合作进展、联系人、成交项目、商机、地点、销售常驻点与渠道合作点的字段及数值范围约束；公开单位 DTO 排除负责人、联系人、备注与详细位置，公开渠道 DTO 排除合同、备注等管理字段。 |
| `app/services/auth.py` | 单管理员密码哈希、服务端会话创建/撤销与权限依赖。 |
| `app/services/organizations.py` | 单位名称标准化、同名新增/改名提醒、`EXISTS` 地点筛选分页、省级聚合、地点点位和完整档案事务服务；公开列表使用独立轻量查询与 SQL 证据计数。管理员坐标统一从 GCJ-02 转为 WGS84 PostGIS 点，列表与导出复用同一筛选语义。 |
| `app/services/sales_office_locations.py` | 销售常驻点公开启用点查询、管理员全量查询与带审计的字段更新服务。 |
| `app/services/channel_partner_locations.py` | 渠道合作点公开安全地图查询、管理员全量查询与带审计的字段更新服务；业务坐标为空时仅为地图绘制回退到演示定位坐标。 |
| `app/services/organization_exports.py` | 使用 OpenPyXL 生成单位审核 Excel，保留单位、地点、状态和来源证据字段；所有外部/管理员文本写入前防公式注入，不导出受保护联系人字段。 |
| `app/services/imports.py` | 批次导入核心服务；保存原始行、可配置类型的官方证据、默认状态并将重复项标记为候选而非覆盖；首次导入或幂等重跑会把同一官方来源中同名且尚未关联的原始行回写到正式档案，不依赖易变化的处理中状态文案；教育部普通高校底表本身不会以校名推测专业后自动创建正式单位。 |
| `app/services/official_sources.py` | 官方公开来源的通用获取服务；提供 `.env` 可配置（默认 4、范围 1–8）的低并发分页、有限重试、中文编码兼容和页序保留，供未来高校、疾控、食药、环保、公安及研究院名单导入复用。 |
| `app/services/geocoding.py` | 高德 Web 服务地址编码；仅将门牌号/兴趣点等可靠结果，或经同名/同校校区与门牌号双重 POI 校验的结果，写为 AMap 的 GCJ-02 pin，并同步写入 WGS84 PostGIS 点位。 |
| `app/cli/import_c9_universities.py` | C9 九所高校的首批真实导入命令；每条使用官方化学/材料相关院系证据，作为筛选功能验证数据。 |
| `app/cli/import_verified_universities_batch_01.py` | 非 C9 高校逐校官网取证首批命令；保存专业依据、完整校址与筛选标签，创建正式单位并回写教育部底表处理状态。 |
| `app/cli/import_verified_double_first_class_universities.py` | 第二轮“双一流”新增建设高校差集导入命令；31 所逐校筛选后保存 25 所合格高校的官网专业证据，并明确保留 6 所艺术/外交类排除结论。 |
| `app/cli/import_verified_provincial_key_universities_batch_01.py` | 省属重点本科首批导入命令；覆盖华北、东北 23 所由官网确认省属重点/省内双一流/高水平建设层次且具备生化环材、医药或检测方向的公办本科，并以低并发队列定位主校区。 |
| `app/cli/import_verified_provincial_key_universities_batch_02.py` | 省属重点本科第 02 批导入命令；覆盖上海、江苏、浙江 24 所由官网确认省级重点/高水平建设层次且具备生化环材、医药、食品农业或检测方向的公办本科，并以严格主校区 POI 队列定位。 |
| `app/cli/import_verified_provincial_key_universities_batch_03.py` | 省属重点本科第 03 批导入命令；按皖闽赣鲁省级重点、高水平或一流学科建设名单筛选 44 所具备生化环材、医药、食品农业或检测方向的公办本科，排除既有和纯财经高校，并以严格主校区 POI 队列定位。 |
| `app/cli/import_verified_provincial_key_universities_batch_04.py` | 省属重点本科第 04 批导入命令；按豫鄂湘粤省级双一流、高水平、冲补强或一流学科建设范围筛选 49 所具备生化环材、医药、食品农业或检测方向的公办本科，按教育部批复使用“湖南理工大学”现名，排除既有、纯文财经艺术、中外合作和非独立分校区，并以严格主校区 POI 队列定位。 |
| `app/cli/import_verified_provincial_key_universities_batch_05.py` | 省属重点本科第 05 批导入命令；按桂琼渝川自治区/省市一流、高水平、四新或贡嘎计划建设证据筛选 37 所具备生化环材、医药、食品农业、安全质量或检测方向的公办本科，使用教育部底表当前校名，排除既有、纯文财经艺术、民办及证据尚不完整院校，并以严格主校区 POI 队列定位。 |
| `app/cli/import_verified_provincial_key_universities_batch_06.py` | 省属重点本科第 06 批导入命令；补齐四川困难证据批 8 所具备贡嘎/省级一流建设身份及生化环材、食品农业或检测方向的公办普通本科，并固化艺术财经、职业本科、公安专批及“有相关专业但证据不足”暂缓项的逐校原因。 |
| `app/cli/import_verified_provincial_key_universities_batch_07.py` | 省属重点本科第 07 批导入命令；覆盖贵州、云南、西藏 17 所具备省属重点/一流建设身份及生化环材、医药、农林食品或检测方向的公办普通本科，区分既有、财经艺术、公安、职业、民办、证据不足和跨省校址项，并以严格主校区 POI 队列定位。 |
| `app/cli/import_verified_provincial_key_universities_batch_08.py` | 省属重点本科第 08 批导入命令；覆盖陕西、甘肃、青海、宁夏、新疆 27 所具备省级重点/一流建设身份及生化环材、医药、农林食品或检测方向的公办普通本科；西藏民族大学按实际主校区归入陕西，并使用教育部 2026 底表的具体来源页回写追溯状态。 |
| `app/cli/import_verified_provincial_key_universities_batch_09.py` | 省属重点本科第 09 批导入命令；覆盖北京 12、天津 8 所具备双一流、市级高精尖/一流或高水平建设身份及生化环材、医药、食品或检测方向的公办普通本科，并记录既有、行业不符、公安、证据不足、职业和民办边界原因；长校名无法稳定命中时使用官网法定主校区地址。 |
| `app/cli/import_verified_public_security_universities.py` | 公安/公共安全本科专批命令；以教育部 2026 普通高校目录全量纳入 33 所公安、警察、刑事、司法警官和消防救援本科院校，保留 23 所专科警校为后续边界清单，并以低并发队列定位主校区；对南京/江苏、郑州/河南等同城易混淆校名使用官方门牌地址。 |
| `app/cli/import_verified_ordinary_undergraduate_universities_batch_01.py` | 普通公办本科第 01 批导入命令；从教育部 2026 高校底表筛选河北 27、山西 19 所具备生化环材、医药、食品农业或检测方向的剩余公办本科，固化 4 所财经/传媒院校的排除原因，并以低并发队列定位主校区；新更名的应急管理大学使用招生官网法定地址避免同名 POI 缺失。 |
| `app/cli/import_verified_ordinary_undergraduate_universities_batch_02.py` | 普通公办本科第 02 批导入命令；从教育部 2026 高校底表筛选内蒙古 11、辽宁 25 所具备生化环材、医药、食品农业或检测方向的剩余公办本科，固化 9 所财经/外语/艺术/职业本科边界原因，并以低并发队列定位主校区；新升格的朝阳师范学院使用招生章程法定地址。 |
| `app/cli/import_verified_ordinary_undergraduate_universities_batch_03.py` | 普通公办本科第 03 批导入命令；从教育部 2026 高校底表筛选吉林 13、黑龙江 15 所具备生化环材、医药、食品农业或检测方向的剩余公办本科，固化 10 所财经/艺术/职业本科边界原因，并复用低并发严格主校区 POI 队列定位。 |
| `app/cli/import_verified_ordinary_undergraduate_universities_batch_04.py` | 普通公办本科第 04 批导入命令；对账教育部 2026 高校底表与正式单位库，筛选上海 7、江苏 20、浙江 16 所具备生化环材、医药、食品或检测方向的剩余公办普通本科，逐校保留官网专业证据，固化 18 所财经/外语/政法/艺术/职业本科边界原因，并复用低并发严格主校区 POI 队列定位。 |
| `app/cli/import_verified_ordinary_undergraduate_universities_batch_05.py` | 普通公办本科第 05 批导入命令；对账教育部 2026 高校底表与正式单位库，筛选安徽 21、福建 9、江西 12、山东 19 所具备生化环材、医药、食品或检测方向的剩余公办普通本科，固化 27 所职业本科及纯财经/艺术/政法等边界原因，并复用低并发严格主校区 POI 队列定位。 |
| `app/cli/import_verified_ordinary_undergraduate_universities_batch_06.py` | 普通公办本科第 06 批导入命令；对账教育部 2026 高校底表与正式单位库，筛选河南 26、湖北 11、湖南 13、广东 5 所具备生化环材、医药、食品或检测方向的剩余公办普通本科，固化 42 所职业本科、合作办学及行业不符/证据不足边界原因，并复用低并发严格主校区 POI 队列定位。 |
| `app/cli/import_moe_university_directory.py` | 教育部 2026 年全国普通高校底表导入命令；复用通用官方来源服务分页读取 2,952 条记录，按 20 页输出进度，写入可追溯 `import_batch/import_row`，再分流为生环化材取证或体育例外取证队列。 |
| `app/cli/geocode_pending_sites.py` | 待编码地点任务入口；读取服务端 Web Service Key，批量创建可靠地图 pin；兼容高德“门牌号”和“门址”两种等价精确等级。 |
| `app/routers/health.py` | 无认证健康检查。 |
| `app/routers/auth.py` | 登录、退出和当前会话 API。 |
| `app/routers/organizations.py` | 单位列表、详情、筛选选项、公开省级热力聚合、管理员地图 pin、完整单位及关联记录原子创建、原子编辑、删除、审核与“按当前筛选条件导出 Excel” API；所有写入口均要求管理员会话。 |
| `app/routers/sales_office_locations.py` | 匿名启用常驻点读取，以及受管理员会话保护的全量读取和字段修改 API。 |
| `app/routers/channel_partner_locations.py` | 匿名渠道地图点读取，以及受管理员会话保护的完整字段读取和修改 API。 |
| `app/main.py` | FastAPI 应用组合、CORS 与 `/api/v1` 路由注册。 |
| `alembic/` | Alembic 迁移环境、首版 `20260805_0001` 结构、`20260810_0002` 可编辑销售常驻点、`20260810_0003` 渠道合作点表及 `20260810_0004` 单位最近跟进/负责人/合作字段；0002 与 0003 分别提供 9 条与 18 条演示数据，0004 不写入业务数据。 |
| `Dockerfile` / `.dockerignore` | API 容器镜像与构建上下文控制。 |
| `tests/test_api_contracts.py` | 不依赖真实客户数据的 API 合同测试：健康检查、权限、公开省级热力/常驻点/渠道点安全读取、公开最近跟进字段与敏感字段隔离、管理员单位及关联商业记录原子新增/修改、创建省市必填与重复提醒、失败事务回滚、子记录归属输入校验、证据约束和体育例外。 |
| `tests/test_organization_exports.py` | 单位 Excel 导出离线测试：验证审核列、地址、来源证据及公式注入防护。 |
| `tests/test_moe_university_directory_import.py` | 教育部高校目录导入的离线单元测试：验证七列解析、体育高校证据分流，以及首次专批遇到既有正式单位时的底表回写，不读取外网或真实数据库。 |
| `tests/test_verified_universities_batch_01.py` | 首批逐校官网取证名单的离线校验：验证官网证据、完整校址和审核标签。 |
| `tests/test_verified_double_first_class_universities.py` | 新增“双一流”差集离线校验：锁定 25 所纳入、6 所排除、官网证据和严格主校区 POI 检索输入。 |
| `tests/test_verified_provincial_key_universities_batch_01.py` | 省属重点本科第 01 批离线校验：锁定 23 所范围、六个省级区域、官网证据和严格主校区 POI 检索输入。 |
| `tests/test_verified_provincial_key_universities_batch_02.py` | 省属重点本科第 02 批离线校验：锁定华东三地 24 所范围、官网证据和严格主校区 POI 检索输入。 |
| `tests/test_verified_provincial_key_universities_batch_03.py` | 省属重点本科第 03 批离线校验：锁定皖闽赣鲁 44 所范围、省份数量、排除项、官方证据和严格主校区 POI 检索输入。 |
| `tests/test_verified_provincial_key_universities_batch_04.py` | 省属重点本科第 04 批离线校验：锁定豫鄂湘粤 49 所范围、省份数量、边界排除项、官方证据和严格主校区 POI 检索输入。 |
| `tests/test_verified_provincial_key_universities_batch_05.py` | 省属重点本科第 05 批离线校验：锁定桂琼渝川 37 所范围、地区数量、既有/边界排除项、官方证据和严格主校区 POI 检索输入。 |
| `tests/test_verified_provincial_key_universities_batch_06.py` | 省属重点本科第 06 批离线校验：锁定四川 8 所困难证据候选、逐校不纳入/暂缓原因、官方证据和严格主校区 POI 检索输入。 |
| `tests/test_verified_provincial_key_universities_batch_07.py` | 省属重点本科第 07 批离线校验：锁定贵州 7、云南 8、西藏 2 所目标高校、边界排除原因、官方证据和严格主校区 POI 检索输入。 |
| `tests/test_verified_provincial_key_universities_batch_08.py` | 省属重点本科第 08 批离线校验：锁定陕西 12、甘肃 7、青海 2、宁夏 1、新疆 5 所目标高校、边界排除原因、教育部底表来源、官方证据和严格主校区 POI 检索输入。 |
| `tests/test_verified_provincial_key_universities_batch_09.py` | 省属重点本科第 09 批离线校验：锁定北京 12、天津 8 所目标高校、边界排除原因、教育部底表来源、公开证据和严格主校区 POI 检索输入。 |
| `tests/test_verified_public_security_universities.py` | 公安/公共安全本科专批离线校验：锁定 33 所本科、23 所专科边界、教育部官方目录证据、业务理由和严格主校区地理编码输入。 |
| `tests/test_verified_ordinary_undergraduate_universities_batch_01.py` | 普通公办本科第 01 批离线校验：锁定河北 27、山西 19 所目标高校、4 所财经/传媒边界、公开专业证据和严格主校区地理编码输入。 |
| `tests/test_verified_ordinary_undergraduate_universities_batch_02.py` | 普通公办本科第 02 批离线校验：锁定内蒙古 11、辽宁 25 所目标高校、9 所财经/外语/艺术/职业本科边界、公开专业证据和严格主校区地理编码输入。 |
| `tests/test_verified_ordinary_undergraduate_universities_batch_03.py` | 普通公办本科第 03 批离线校验：锁定吉林 13、黑龙江 15 所目标高校、10 所财经/艺术/职业本科边界、公开专业证据和严格主校区地理编码输入。 |
| `tests/test_verified_ordinary_undergraduate_universities_batch_04.py` | 普通公办本科第 04 批离线校验：锁定上海 7、江苏 20、浙江 16 所目标高校、18 所行业/职业本科边界、公开专业证据和严格主校区地理编码输入。 |
| `tests/test_verified_ordinary_undergraduate_universities_batch_05.py` | 普通公办本科第 05 批离线校验：锁定安徽 21、福建 9、江西 12、山东 19 所目标高校、27 所行业/职业本科边界、公开专业证据和严格主校区地理编码输入。 |
| `tests/test_verified_ordinary_undergraduate_universities_batch_06.py` | 普通公办本科第 06 批离线校验：锁定河南 26、湖北 11、湖南 13、广东 5 所目标高校、42 所职业/合作办学/行业边界、公开专业证据和严格主校区地理编码输入。 |
| `tests/test_official_sources.py` | 通用官方来源获取服务的离线单元测试：验证中文编码、传输中断重试、低并发页序与并发安全边界。 |
| `requirements.txt` | FastAPI、SQLAlchemy、Alembic、PostgreSQL 驱动、认证、PostGIS、Excel 与 Redis 依赖。 |
| `requirements-dev.txt` | 后端开发、测试、静态检查与浏览器自动化依赖，并通过 `-r requirements.txt` 引入运行时依赖。 |

## 数据库

数据库使用 Docker 内部网络的 PostgreSQL 16 + PostGIS，不发布数据库端口，避免与本机已有 PostgreSQL 冲突。`organization` 是已完成纳入依据核验的单位主档案，并保存最近跟进时间/内容、跟进负责人、合作意向及合作等级；`organization_site` 是一对多地点与坐标；`organization_evidence` 记录官方纳入依据；`sales_office_location` 独立保存可由管理员调整的销售常驻点地址、GCJ-02 坐标、覆盖半径和启用状态；`import_batch` 与 `import_row` 保存来源范围、原始行和去重结果。教育部全国普通高校名单首先只进入后两张表：体育类高校等待体育例外依据，其他高校等待生物、环境、化学、材料相关专业/院系/科研依据，不能仅凭学校名称进入 `organization`。`organization_contact` 保存一对多联系人，`opportunity` 保存推进中的一对多商机，`sales_project` 保存一对多成交项目及 `NUMERIC` 成交额；三类子记录只通过管理员 DTO 维护，公开列表不返回联系人。新增字段使用 Alembic 迁移，少量临时信息放入 `organization.attributes JSONB`。`organization_site.longitude/latitude` 保存 AMap 直接显示的 GCJ-02 坐标，`location` 则保存转换后的 WGS84（SRID 4326）PostGIS 点位；只有通过服务端地理编码的可靠地址才会生成地图 pin。

## 容器与网关

渠道网络由 `channel_partner_location` 独立持久化：管理接口可维护完整业务字段，匿名地图接口仅投影名称、类型、展示坐标、半径与合作等级。当前 18 条演示记录的业务经纬度、授权区域、产品线、合同和备注均为空；地图所需的省会中心点保存在独立演示坐标列，避免把演示位置误当成已核验业务坐标。

| 路径 | 作用 |
| --- | --- |
| `docker-compose.yml` | 固定 Compose ASCII 项目名 `unite-sales-map`，在一个内部网络启动 PostGIS、Redis、FastAPI、Next.js 与 Nginx；Web 使用镜像内已编译的生产产物，不挂载会遮蔽 `.next` 的匿名卷；仅网关向主机暴露 `.env` 的 `APP_PORT`。同时将官方名单的低并发、重试和超时变量传入 API，便于不改代码地调整采集策略。 |
| `infra/nginx/default.conf.template` | 将 `/api/*` 转发给 FastAPI、将网页转发给 Next.js；按高德官方配置以 `/_AMapService/` 固定一级路由代理 Web 服务及自定义样式请求，网关追加安全密钥，浏览器不会获得该密钥。 |

## 文档与协作文件

| 路径 | 作用 |
| --- | --- |
| `docs/PROJECT_ARCHITECTURE.md` | 本文件：维护仓库结构、文件职责、已实现范围与规划边界。 |
| `docs/全国销售网络作战地图系统 - 需求说明书 V1.0 20260803.docx` | 业务需求说明书源文件。 |
| `docs/~$销售网络作战地图系统 - 需求说明书 V1.0 20260803.docx` | Office 打开 Word 文件时产生的临时锁定文件；关闭文档后可由 Office 自动移除。 |
| `AGENTS.md` | 全局开发约定，包括代码注释、文档同步、路径、测试、安全规则，以及 Ponytail、Caveman、Karpathy Guidelines 与 Awesome DESIGN.md 的每轮技能路由。 |
| `PRODUCT.md` | 产品定位、用户、能力边界与视觉原则，供设计和实现时参考。 |
| `README.md` | 实际环境变量、Docker 启动/停止、健康检查、本地校验与数据导入原则。 |

## 强制执行基线

- 本仓库唯一默认根目录为 `D:\桌面\优纳特销售网站`。所有终端操作以 `Set-Location -LiteralPath 'D:\桌面\优纳特销售网站'` 开始，不再使用 C 盘旧路径。
- 每轮执行、测试或代码生成前必须先完整读取根目录 `AGENTS.md`，再列出并检查本轮所需的应用、服务、环境变量与库；依赖缺失且无法安全自动安装时，停止实现并等待用户处理。
- 每次新增或修改源码、SQL、数据库迁移、配置、脚本或目录，都必须同步更新本文件的真实结构、文件职责与实现状态。若本文件未同步，变更视为未完成。
- 代码文件顶部和所有新增/修改的具名入口必须具有职责注释，重点说明“为什么存在、负责什么”；生成物与第三方文件除外。
- 用户级 Codex 技能安装在 `C:\Users\alien\.codex\skills\`，不复制进仓库或容器镜像。每轮由根 `AGENTS.md` 检查并路由：编码任务使用 Ponytail 与 Karpathy Guidelines，用户说明采用 Caveman `lite`，前端视觉任务使用 Awesome DESIGN.md；第三方可执行 hooks 默认禁用。

## 维护规则

首页单位热力图在地图容器内缩放居中，完整保留南部边界；选中省份使用独立 SVG 描边层且统计弹层置顶。地图框左下角的缩放控件以完整视图为默认和最小尺寸，可逐级放大、缩小并一键复位。销售常驻点以及经销商、代理商、合作伙伴覆盖层均默认隐藏，与热力图同步缩放，不能遮挡省份点击或统计弹层；合作等级只影响三类渠道覆盖层，不改变省级热力统计。

新增、移动、删除源码/素材/配置文件时，必须同时更新本文件对应条目。每个可维护的代码文件应在文件开头用一到两行说明模块职责及主要库；新增或修改具名函数、组件、路由处理器时，也应添加简短职责注释。生成文件（如 `next-env.d.ts`）、第三方依赖和二进制素材不手工添加注释。
