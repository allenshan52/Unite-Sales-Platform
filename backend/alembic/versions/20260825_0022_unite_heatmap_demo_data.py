"""扩充优纳特成交与采购意向的虚构演示数据，支撑省级金额热力图。"""

from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260825_0022"
down_revision = "20260825_0021"
branch_labels = None
depends_on = None


def _uuid(number: int) -> str:
    """生成迁移专用稳定 UUID，使演示数据可验证并可精确回滚。"""

    return f"00000000-0000-4000-8000-{number:012d}"


# 坐标同时保存高德使用的 GCJ-02 与 PostGIS 使用的 WGS84，所有名称和地址均明确标记为演示。
CUSTOMERS = (
    (1, "优纳特演示成交单位07", "检验检测", "辽宁省", "大连市", "甘井子区", "210200", 121.6147, 38.9140, 121.60975671109382, 38.913222734216795, "二级"),
    (2, "优纳特演示成交单位08", "海洋科研", "山东省", "青岛市", "崂山区", "370200", 120.3826, 36.0671, 120.37746691995753, 36.066823772440394, "一级"),
    (3, "优纳特演示成交单位09", "食品安全", "河南省", "郑州市", "高新区", "410100", 113.6254, 34.7466, 113.6193533355415, 34.74778254852426, "二级"),
    (4, "优纳特演示成交单位10", "生命科学", "湖北省", "武汉市", "江夏区", "420100", 114.3054, 30.5931, 114.29995522380862, 30.59550949143213, "一级"),
    (5, "优纳特演示成交单位11", "材料分析", "湖南省", "长沙市", "岳麓区", "430100", 112.9388, 28.2282, 112.93335022455615, 28.23170758269778, "二级"),
    (6, "优纳特演示成交单位12", "生物医药", "四川省", "成都市", "武侯区", "510100", 104.0665, 30.5723, 104.06399509432929, 30.574754459280392, "一级"),
    (7, "优纳特演示成交单位13", "能源化工", "陕西省", "西安市", "雁塔区", "610100", 108.9398, 34.3416, 108.93514436572545, 34.343155504344615, "一级"),
    (8, "优纳特演示成交单位14", "环境监测", "福建省", "厦门市", "湖里区", "350200", 118.0894, 24.4798, 118.08442291641654, 24.482446768046653, "二级"),
    (9, "优纳特演示成交单位15", "精细化工", "安徽省", "合肥市", "蜀山区", "340100", 117.2272, 31.8206, 117.22171770390509, 31.822599149965356, "三级"),
    (10, "优纳特演示成交单位16", "公共卫生", "河北省", "石家庄市", "裕华区", "130100", 114.5149, 38.0428, 114.50892645768306, 38.042181120914925, "二级"),
    (11, "优纳特演示成交单位17", "高校科研", "江西省", "南昌市", "红谷滩区", "360100", 115.8582, 28.6829, 115.8532995268804, 28.68623012545638, "三级"),
    (12, "优纳特演示成交单位18", "农业检测", "云南省", "昆明市", "呈贡区", "530100", 102.8329, 24.8801, 102.83148380564772, 24.883169223589267, "二级"),
)

PROJECTS = (
    (1, 1, 2, "演示项目07-A：实验室基础设备", "95000.00", date(2024, 3, 12)),
    (2, 1, 2, "演示项目07-B：检测模块扩容", "180000.00", date(2025, 10, 20)),
    (3, 2, 3, "演示项目08-A：海洋样品分析平台", "320000.00", date(2024, 8, 8)),
    (4, 2, 3, "演示项目08-B：自动进样系统", "410000.00", date(2026, 2, 17)),
    (5, 3, 5, "演示项目09：食品安全检测平台", "560000.00", date(2025, 5, 23)),
    (6, 4, 5, "演示项目10-A：生命科学分析平台", "850000.00", date(2024, 11, 6)),
    (7, 4, 5, "演示项目10-B：高通量检测产线", "1250000.00", date(2026, 4, 28)),
    (8, 5, 5, "演示项目11：材料表征系统", "1700000.00", date(2025, 7, 16)),
    (9, 6, 4, "演示项目12-A：生物医药研发平台", "2600000.00", date(2024, 12, 19)),
    (10, 6, 4, "演示项目12-B：应用方法升级", "550000.00", date(2026, 6, 3)),
    (11, 7, 4, "演示项目13：能源化工联合实验室", "4200000.00", date(2025, 9, 11)),
    (12, 8, 6, "演示项目14-A：移动环境监测设备", "230000.00", date(2024, 6, 14)),
    (13, 8, 6, "演示项目14-B：区域监测平台", "1080000.00", date(2026, 3, 25)),
    (14, 9, 6, "演示项目15：精细化工分析系统", "680000.00", date(2025, 1, 9)),
    (15, 10, 2, "演示项目16-A：公共卫生检测设备", "1450000.00", date(2024, 9, 27)),
    (16, 10, 2, "演示项目16-B：实验室信息化升级", "350000.00", date(2026, 5, 19)),
    (17, 11, 6, "演示项目17：高校基础教学设备", "120000.00", date(2025, 12, 5)),
    (18, 12, 4, "演示项目18：农业质量检测中心", "2100000.00", date(2025, 4, 22)),
)

OPPORTUNITIES = (
    (1, 1, 2, "演示意向07-A：自动化前处理", "已识别", "180000.00", date(2026, 10, 9)),
    (2, 1, 2, "演示意向07-B：年度耗材框架", "资格确认", "360000.00", date(2026, 11, 18)),
    (3, 2, 3, "演示意向08-A：船载检测模块", "方案/报价", "750000.00", date(2026, 9, 22)),
    (4, 2, 3, "演示意向08-B：海洋监测二期", "商务谈判", "1100000.00", date(2026, 9, 5)),
    (5, 3, 5, "演示意向09：快速筛查设备", "资格确认", "220000.00", date(2026, 12, 2)),
    (6, 4, 5, "演示意向10-A：细胞分析平台", "商务谈判", "1800000.00", date(2026, 9, 12)),
    (7, 4, 5, "演示意向10-B：样本存储升级", "方案/报价", "450000.00", date(2026, 10, 26)),
    (8, 5, 5, "演示意向11：材料分析中心二期", "已识别", "2600000.00", date(2027, 1, 14)),
    (9, 6, 4, "演示意向12-A：智能实验室改造", "商务谈判", "950000.00", date(2026, 9, 8)),
    (10, 6, 4, "演示意向12-B：检测方法包", "资格确认", "320000.00", date(2026, 11, 7)),
    (11, 7, 4, "演示意向13：新能源联合平台", "方案/报价", "4800000.00", date(2026, 10, 15)),
    (12, 8, 6, "演示意向14：空气监测网络", "资格确认", "580000.00", date(2026, 12, 11)),
    (13, 9, 6, "演示意向15-A：工艺分析设备", "已识别", "1350000.00", date(2027, 2, 20)),
    (14, 9, 6, "演示意向15-B：年度技术服务", "方案/报价", "290000.00", date(2026, 10, 31)),
)


def _validate_demo_data() -> None:
    """在写库前锁定数量、省份和金额梯度，避免演示迁移静默退化。"""

    province_by_customer = {number: province for number, _name, _industry, province, *_rest in CUSTOMERS}
    province_totals: dict[str, Decimal] = defaultdict(Decimal)
    for _number, customer_number, _salesperson_number, _name, amount, _signed_at in PROJECTS:
        province_totals[province_by_customer[customer_number]] += Decimal(amount)

    assert len(CUSTOMERS) == 12
    assert len(PROJECTS) == 18
    assert len(OPPORTUNITIES) == 14
    assert len(set(province_by_customer.values())) == 12
    assert all(Decimal(project[4]) > 0 for project in PROJECTS)
    assert all(Decimal(opportunity[5]) > 0 for opportunity in OPPORTUNITIES)
    assert any(total < Decimal(250000) for total in province_totals.values())
    assert any(Decimal(250000) <= total < Decimal(500000) for total in province_totals.values())
    assert any(Decimal(500000) <= total < Decimal(1000000) for total in province_totals.values())
    assert any(Decimal(1000000) <= total < Decimal(2000000) for total in province_totals.values())
    assert any(total >= Decimal(2000000) for total in province_totals.values())


def upgrade() -> None:
    """新增跨十二省的虚构客户、成交合同和未成交采购意向。"""

    _validate_demo_data()
    organization_table = sa.table(
        "organization",
        *[sa.column(name) for name in (
            "id", "name", "normalized_name", "organization_type", "industry", "customer_status",
            "review_status", "inclusion_reason", "is_sports_exception", "recent_follow_up_at",
            "recent_follow_up_content", "cooperation_intent", "cooperation_level", "notes",
        )],
        sa.column("attributes", postgresql.JSONB()),
    )
    site_table = sa.table(
        "organization_site",
        *[sa.column(name) for name in (
            "id", "organization_id", "site_name", "raw_address", "address", "province", "city", "district",
            "amap_adcode", "geocode_status", "geocode_confidence", "longitude", "latitude", "is_primary",
        )],
    )
    project_table = sa.table(
        "sales_project",
        *[sa.column(name) for name in (
            "id", "organization_id", "opportunity_id", "salesperson_id", "name", "contract_amount",
            "signed_at", "project_detail",
        )],
    )
    opportunity_table = sa.table(
        "opportunity",
        *[sa.column(name) for name in (
            "id", "organization_id", "salesperson_id", "title", "stage", "estimated_amount", "ai_summary",
            "next_action", "next_action_at",
        )],
    )
    now = datetime(2026, 8, 25, 9, tzinfo=UTC)

    op.bulk_insert(organization_table, [{
        "id": _uuid(22000 + number),
        "name": name,
        "normalized_name": name.lower(),
        "organization_type": "企业",
        "industry": industry,
        "customer_status": "已成交客户",
        "review_status": "已核验",
        "inclusion_reason": "优纳特省级成交金额热力图虚构演示数据",
        "is_sports_exception": False,
        "recent_follow_up_at": now,
        "recent_follow_up_content": "演示跟进：已完成合同交付并持续跟进复购意向",
        "cooperation_intent": "演示合作：已成交并存在后续采购可能",
        "cooperation_level": cooperation_level,
        "attributes": {"demo": True, "unite_heatmap_demo": True},
        "notes": "纯虚构单位，仅用于优纳特成交与采购意向热力图演示",
    } for number, name, industry, _province, _city, _district, _adcode, _longitude, _latitude, _wgs_longitude, _wgs_latitude, cooperation_level in CUSTOMERS])

    op.bulk_insert(site_table, [{
        "id": _uuid(22100 + number),
        "organization_id": _uuid(22000 + number),
        "site_name": f"{name}演示主地点",
        "raw_address": f"{city}{district}演示产业园{number}号",
        "address": f"{city}{district}演示产业园{number}号",
        "province": province,
        "city": city,
        "district": district,
        "amap_adcode": adcode,
        "geocode_status": "已定位",
        "geocode_confidence": 100,
        "longitude": longitude,
        "latitude": latitude,
        "is_primary": True,
    } for number, name, _industry, province, city, district, adcode, longitude, latitude, _wgs_longitude, _wgs_latitude, _cooperation_level in CUSTOMERS])

    connection = op.get_bind()
    for number, _name, _industry, _province, _city, _district, _adcode, _longitude, _latitude, wgs_longitude, wgs_latitude, _cooperation_level in CUSTOMERS:
        connection.execute(
            sa.text("""
                UPDATE organization_site
                SET location = ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)
                WHERE id = :site_id
            """),
            {"site_id": _uuid(22100 + number), "longitude": wgs_longitude, "latitude": wgs_latitude},
        )

    op.bulk_insert(project_table, [{
        "id": _uuid(22200 + number),
        "organization_id": _uuid(22000 + customer_number),
        "opportunity_id": None,
        "salesperson_id": _uuid(8000 + salesperson_number),
        "name": name,
        "contract_amount": Decimal(amount),
        "signed_at": signed_at,
        "project_detail": "纯虚构演示成交；详情卡金额使用本记录合同总金额",
    } for number, customer_number, salesperson_number, name, amount, signed_at in PROJECTS])

    op.bulk_insert(opportunity_table, [{
        "id": _uuid(22300 + number),
        "organization_id": _uuid(22000 + customer_number),
        "salesperson_id": _uuid(8000 + salesperson_number),
        "title": title,
        "stage": stage,
        "estimated_amount": Decimal(amount),
        "ai_summary": "纯虚构采购意向，仅用于优纳特未成交金额热力叠加演示",
        "next_action": "演示下一步：确认预算、技术范围与采购计划",
        "next_action_at": next_action_at,
    } for number, customer_number, salesperson_number, title, stage, amount, next_action_at in OPPORTUNITIES])


def downgrade() -> None:
    """仅删除本迁移写入的虚构成交、意向、地点与单位。"""

    op.execute(sa.text("DELETE FROM opportunity WHERE id BETWEEN :first_id AND :last_id").bindparams(
        first_id=_uuid(22301), last_id=_uuid(22300 + len(OPPORTUNITIES)),
    ))
    op.execute(sa.text("DELETE FROM sales_project WHERE id BETWEEN :first_id AND :last_id").bindparams(
        first_id=_uuid(22201), last_id=_uuid(22200 + len(PROJECTS)),
    ))
    op.execute(sa.text("DELETE FROM organization_site WHERE id BETWEEN :first_id AND :last_id").bindparams(
        first_id=_uuid(22101), last_id=_uuid(22100 + len(CUSTOMERS)),
    ))
    op.execute(sa.text("DELETE FROM organization WHERE id BETWEEN :first_id AND :last_id").bindparams(
        first_id=_uuid(22001), last_id=_uuid(22000 + len(CUSTOMERS)),
    ))
