"""创建一省一案典型案例表，并写入六条纯虚构、可公开的演示案例。"""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260818_0014"
down_revision = "20260818_0013"
branch_labels = None
depends_on = None


def _uuid(number: int) -> str:
    """生成稳定 UUID，便于验证演示数据和安全回滚。"""

    return f"00000000-0000-4000-8000-{number:012d}"


CASES = (
    {
        "number": 1, "project_number": 1, "province": "江苏省", "province_adcode": "320000", "city": "盐城市",
        "title": "沿海产业园实验室分析能力升级", "subtitle": "从分散检测到统一方法平台",
        "customer_display_name": "江苏某产业检测中心（演示）", "industry_label": "实验室分析设备",
        "summary": "围绕产业园日常质量控制需求，建设覆盖样品前处理、分析检测与方法培训的一体化演示平台。",
        "challenge": "原有仪器分散在多个实验区，方法版本不统一，新员工需要较长时间才能独立完成检测，旺季样品周转压力明显。",
        "solution": "按高频样品流程重新规划设备组合，统一十二项常用方法模板，并以分批安装、现场验证和岗位培训降低切换风险。",
        "outcome": "演示项目在八周内完成部署，核心方法形成统一作业版本，二十四名实验人员完成岗位培训，后续耗材供应纳入年度计划。",
        "product_scope": "实验室分析设备、样品前处理组件、安装验证、方法培训与年度耗材建议。",
        "customer_quote": "新的流程让检测任务、方法和培训终于能在同一套标准下运行。",
        "quote_attribution": "项目实验室负责人（虚构）", "show_contract_amount": True, "is_featured": False,
        "images": [{"path": "/cases/jiangsu-lab.webp", "alt_text": "虚构的江苏产业检测实验室分析平台", "caption": "演示图片：统一规划后的检测工作区", "is_cover": True}],
        "metrics": [{"label": "部署周期", "value": "8", "unit": "周"}, {"label": "方法覆盖", "value": "12", "unit": "项"}, {"label": "培训人员", "value": "24", "unit": "人"}],
    },
    {
        "number": 2, "project_number": 3, "province": "吉林省", "province_adcode": "220000", "city": "吉林市",
        "title": "食品安全检测平台标准化建设", "subtitle": "让多品类样品共享一套质量基线",
        "customer_display_name": "吉林某食品检测机构（演示）", "industry_label": "食品安全检测",
        "summary": "针对乳制品、谷物与调味品等多品类检测任务，搭建统一的前处理与分析验证流程。",
        "challenge": "不同品类沿用各自记录方式，重复配制和复测较多，关键方法依赖少数熟练人员，结果复核缺少一致的数据入口。",
        "solution": "梳理代表性样品矩阵，配置共享前处理能力和食品检测设备，建立方法确认清单、质控样流程及分角色培训计划。",
        "outcome": "核心品类形成统一质控模板，复核资料按项目集中归档，跨岗位协作路径更清晰，并具备后续扩展新方法的基础。",
        "product_scope": "食品检测设备、通用前处理工具、方法开发服务、质控流程和操作培训。",
        "customer_quote": "标准化不是增加步骤，而是减少每次从头确认的时间。",
        "quote_attribution": "质量负责人（虚构）", "show_contract_amount": True, "is_featured": False,
        "images": [{"path": "/cases/jilin-food-safety.webp", "alt_text": "虚构的吉林食品安全检测实验室", "caption": "演示图片：食品样品标准化检测场景", "is_cover": True}],
        "metrics": [{"label": "覆盖品类", "value": "3", "unit": "大类"}, {"label": "质控模板", "value": "9", "unit": "套"}, {"label": "培训岗位", "value": "4", "unit": "类"}],
    },
    {
        "number": 3, "project_number": 4, "province": "广东省", "province_adcode": "440000", "city": "湛江市",
        "title": "多参数环境监测体系落地", "subtitle": "面向沿海场景的连续检测与运维协同",
        "customer_display_name": "广东某环境技术中心（演示）", "industry_label": "环境监测",
        "summary": "建设面向沿海产业场景的多参数环境监测演示系统，并打通校准、巡检与异常复核流程。",
        "challenge": "监测设备型号与维护周期不一致，异常结果需要人工跨表核对，沿海高湿环境也增加了日常巡检和稳定运行难度。",
        "solution": "以统一参数字典组织监测点位，配置多参数分析设备和校准计划，建立异常复核清单及年度技术服务机制。",
        "outcome": "六类关键参数纳入统一监测视图，巡检与校准节点可追踪，异常样品复核路径缩短，年度技术服务已形成固定节奏。",
        "product_scope": "多参数环境监测设备、校准工具、点位规划、巡检模板与年度技术服务。",
        "customer_quote": "设备只是起点，稳定的校准和复核机制才让监测数据真正可用。",
        "quote_attribution": "技术平台主管（虚构）", "show_contract_amount": True, "is_featured": False,
        "images": [{"path": "/cases/guangdong-environment.webp", "alt_text": "虚构的广东沿海环境监测系统", "caption": "演示图片：多参数环境监测与复核工作区", "is_cover": True}],
        "metrics": [{"label": "监测参数", "value": "6", "unit": "类"}, {"label": "交付节点", "value": "5", "unit": "个"}, {"label": "服务周期", "value": "12", "unit": "月"}],
    },
    {
        "number": 4, "project_number": 6, "province": "重庆市", "province_adcode": "500000", "city": "重庆市",
        "title": "生物样品前处理流程重构", "subtitle": "减少批次波动，建立可复现的验证链路",
        "customer_display_name": "重庆某生物技术企业（演示）", "industry_label": "生物样品前处理",
        "summary": "围绕研发样品批次差异，重构前处理设备配置、验证记录与交接培训。",
        "challenge": "样品类型变化快，手工步骤较多，不同操作者之间存在批次差异，研发阶段的处理条件难以快速复制到后续批次。",
        "solution": "选择三类代表性样品验证关键步骤，配置标准化前处理设备，固化参数记录、偏差处理和岗位交接模板。",
        "outcome": "代表性样品形成可复用验证包，关键步骤参数可追溯，研发与检测岗位完成联合培训，批次交接更加稳定。",
        "product_scope": "生物样品前处理设备、验证方案、参数模板、偏差记录和联合培训。",
        "customer_quote": "把经验写进流程后，团队才能稳定复制同一套处理条件。",
        "quote_attribution": "研发项目经理（虚构）", "show_contract_amount": True, "is_featured": False,
        "images": [{"path": "/cases/chongqing-biotech.webp", "alt_text": "虚构的重庆生物样品前处理场景", "caption": "演示图片：标准化生物样品处理工作台", "is_cover": True}],
        "metrics": [{"label": "代表样品", "value": "3", "unit": "类"}, {"label": "验证模板", "value": "7", "unit": "份"}, {"label": "联合培训", "value": "16", "unit": "人"}],
    },
    {
        "number": 5, "project_number": 7, "province": "浙江省", "province_adcode": "330000", "city": "金华市",
        "title": "研发中心分析平台一期", "subtitle": "以统一数据和方法支撑药物研发节奏",
        "customer_display_name": "浙江某医药研发中心（演示）", "industry_label": "医药研发分析",
        "summary": "为研发中心建设一期分析平台，统一设备、方法转移、应用培训和阶段验收。",
        "challenge": "项目团队需要在研发进度、合规记录和新设备学习之间保持平衡，原有分析资源无法同时支撑多个候选项目。",
        "solution": "按研发优先级分阶段部署分析设备，建立方法转移包、应用培训计划和验收清单，让平台能力随项目节奏逐步上线。",
        "outcome": "一期平台按三个阶段完成验收，八套方法完成转移，核心用户具备独立操作能力，并启动后续应用培训服务。",
        "product_scope": "研发分析设备、方法转移、应用培训、阶段验收和后续技术支持。",
        "customer_quote": "分阶段交付让平台能力和研发任务同步成长，没有把风险集中到最后。",
        "quote_attribution": "研发平台主管（虚构）", "show_contract_amount": True, "is_featured": True,
        "images": [{"path": "/cases/zhejiang-pharma.webp", "alt_text": "虚构的浙江医药研发分析平台", "caption": "演示图片：研发中心一期分析平台", "is_cover": True}],
        "metrics": [{"label": "验收阶段", "value": "3", "unit": "个"}, {"label": "方法转移", "value": "8", "unit": "套"}, {"label": "核心用户", "value": "12", "unit": "人"}],
    },
    {
        "number": 6, "project_number": 9, "province": "广西壮族自治区", "province_adcode": "450000", "city": "柳州市",
        "title": "新材料检测产线集成交付", "subtitle": "从单机检测走向连续质量验证",
        "customer_display_name": "广西某新材料企业（演示）", "industry_label": "新材料检测",
        "summary": "围绕新材料研发与小批量生产，集成样品制备、性能检测、数据记录和现场验收能力。",
        "challenge": "研发与生产使用不同检测节奏，单机结果难以形成连续质量证据，样品流转和异常复测缺少统一责任边界。",
        "solution": "按样品流转顺序集成制备与检测设备，定义关键质量节点、异常复测条件和角色责任，并通过联机试运行完成验收。",
        "outcome": "五个质量节点进入统一流程，样品状态可追踪，研发与生产共享同一套复测规则，产线完成连续试运行。",
        "product_scope": "样品制备设备、材料性能检测设备、流程集成、联机试运行和现场验收。",
        "customer_quote": "统一流程后，研发数据终于能顺畅进入生产质量验证。",
        "quote_attribution": "生产质量负责人（虚构）", "show_contract_amount": True, "is_featured": False,
        "images": [{"path": "/cases/guangxi-materials.webp", "alt_text": "虚构的广西新材料检测产线", "caption": "演示图片：新材料样品制备与性能检测", "is_cover": True}],
        "metrics": [{"label": "质量节点", "value": "5", "unit": "个"}, {"label": "集成设备", "value": "6", "unit": "台套"}, {"label": "试运行", "value": "10", "unit": "天"}],
    },
)


def upgrade() -> None:
    """创建案例表、发布唯一约束，并关联现有六笔虚构成交项目。"""

    op.create_table(
        "typical_case",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sales_project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sales_project.id", ondelete="SET NULL")),
        sa.Column("province", sa.String(60), nullable=False),
        sa.Column("province_adcode", sa.String(6), nullable=False),
        sa.Column("city", sa.String(60), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("subtitle", sa.String(240)),
        sa.Column("customer_display_name", sa.String(160), nullable=False),
        sa.Column("industry_label", sa.String(120), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("challenge", sa.Text(), nullable=False),
        sa.Column("solution", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("product_scope", sa.Text(), nullable=False),
        sa.Column("customer_quote", sa.Text()),
        sa.Column("quote_attribution", sa.String(160)),
        sa.Column("show_contract_amount", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("images", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("metrics", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("province_adcode ~ '^[0-9]{6}$'", name="ck_typical_case_province_adcode"),
        sa.CheckConstraint("NOT is_featured OR is_published", name="ck_typical_case_featured_published"),
    )
    op.create_index("ix_typical_case_project", "typical_case", ["sales_project_id"])
    op.create_index("uq_typical_case_published_province", "typical_case", ["province"], unique=True, postgresql_where=sa.text("is_published"))
    op.create_index("uq_typical_case_published_project", "typical_case", ["sales_project_id"], unique=True, postgresql_where=sa.text("is_published AND sales_project_id IS NOT NULL"))
    op.create_index("uq_typical_case_featured", "typical_case", ["is_featured"], unique=True, postgresql_where=sa.text("is_featured"))

    case_table = sa.table(
        "typical_case",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("sales_project_id", postgresql.UUID(as_uuid=True)),
        *[sa.column(name) for name in (
            "province", "province_adcode", "city", "title", "subtitle", "customer_display_name", "industry_label",
            "summary", "challenge", "solution", "outcome", "product_scope", "customer_quote", "quote_attribution",
            "show_contract_amount", "is_published", "published_at", "is_featured",
        )],
        sa.column("images", postgresql.JSONB()),
        sa.column("metrics", postgresql.JSONB()),
    )
    published_at = datetime(2026, 8, 18, 10, tzinfo=UTC)
    op.bulk_insert(case_table, [{
        "id": _uuid(6000 + item["number"]),
        "sales_project_id": _uuid(5300 + item["project_number"]),
        **{key: value for key, value in item.items() if key not in {"number", "project_number"}},
        "is_published": True,
        "published_at": published_at,
    } for item in CASES])


def downgrade() -> None:
    """删除案例表及全部演示内容，不改动被关联的成交项目。"""

    op.drop_index("uq_typical_case_featured", table_name="typical_case", postgresql_where=sa.text("is_featured"))
    op.drop_index("uq_typical_case_published_project", table_name="typical_case", postgresql_where=sa.text("is_published AND sales_project_id IS NOT NULL"))
    op.drop_index("uq_typical_case_published_province", table_name="typical_case", postgresql_where=sa.text("is_published"))
    op.drop_index("ix_typical_case_project", table_name="typical_case")
    op.drop_table("typical_case")
