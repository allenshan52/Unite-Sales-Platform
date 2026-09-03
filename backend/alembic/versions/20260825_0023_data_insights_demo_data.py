"""补齐优纳特全国数据洞察所需的虚构成交、商机与省市覆盖。"""

from collections import Counter
from datetime import UTC, date, datetime
from decimal import Decimal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260825_0023"
down_revision = "20260825_0022"
branch_labels = None
depends_on = None


def _uuid(number: int) -> str:
    """生成迁移专用稳定 UUID，保证虚构数据可验证并可精确回滚。"""

    return f"00000000-0000-4000-8000-{number:012d}"


# 仅补当前成交热力数据未覆盖的十三个省级区域；GCJ-02 与 WGS84 坐标均使用城市内演示点位。
CUSTOMERS = (
    (1, "优纳特演示成交单位19", "生命科学", "北京市", "北京市", "海淀区", "110100", 116.2981, 39.9593, 116.292023176732, 39.958040510062, "一级"),
    (2, "优纳特演示成交单位20", "公共卫生", "北京市", "北京市", "大兴区", "110100", 116.3414, 39.7269, 116.335258407630, 39.725577067731, "二级"),
    (3, "优纳特演示成交单位21", "生物医药", "上海市", "上海市", "浦东新区", "310100", 121.5447, 31.2225, 121.540418074257, 31.224644958269, "一级"),
    (4, "优纳特演示成交单位22", "食品安全", "上海市", "上海市", "闵行区", "310100", 121.3817, 31.1128, 121.377069108298, 31.114704028376, "二级"),
    (5, "优纳特演示成交单位23", "检验检测", "天津市", "天津市", "南开区", "120100", 117.1507, 39.1386, 117.144305820566, 39.137471134375, "二级"),
    (6, "优纳特演示成交单位24", "材料分析", "天津市", "天津市", "滨海新区", "120100", 117.6984, 39.0173, 117.692143465886, 39.016412820365, "三级"),
    (7, "优纳特演示成交单位25", "能源化工", "山西省", "太原市", "小店区", "140100", 112.5657, 37.7369, 112.559451141796, 37.736387042262, "一级"),
    (8, "优纳特演示成交单位26", "环境监测", "山西省", "大同市", "平城区", "140200", 113.3001, 40.0768, 113.293083448803, 40.075600248378, "二级"),
    (9, "优纳特演示成交单位27", "农业检测", "内蒙古自治区", "呼和浩特市", "赛罕区", "150100", 111.7012, 40.7925, 111.694347608940, 40.791135381335, "二级"),
    (10, "优纳特演示成交单位28", "精细化工", "内蒙古自治区", "包头市", "九原区", "150200", 109.9681, 40.6006, 109.962369459892, 40.599459140975, "三级"),
    (11, "优纳特演示成交单位29", "高校科研", "黑龙江省", "哈尔滨市", "松北区", "230100", 126.5103, 45.8022, 126.504159386434, 45.800149898881, "一级"),
    (12, "优纳特演示成交单位30", "石化分析", "黑龙江省", "大庆市", "萨尔图区", "230600", 125.1127, 46.5907, 125.105648102846, 46.588599516465, "二级"),
    (13, "优纳特演示成交单位31", "公共卫生", "海南省", "海口市", "龙华区", "460100", 110.3285, 20.0310, 110.324135183780, 20.033051398472, "一级"),
    (14, "优纳特演示成交单位32", "海洋科研", "海南省", "三亚市", "吉阳区", "460200", 109.5782, 18.2815, 109.574246837754, 18.283355667397, "二级"),
    (15, "优纳特演示成交单位33", "生物医药", "贵州省", "贵阳市", "观山湖区", "520100", 106.6263, 26.6464, 106.622738629738, 26.650073914385, "一级"),
    (16, "优纳特演示成交单位34", "食品安全", "贵州省", "遵义市", "汇川区", "520300", 106.9336, 27.7493, 106.929761972765, 27.752825900958, "二级"),
    (17, "优纳特演示成交单位35", "高原科研", "西藏自治区", "拉萨市", "城关区", "540100", 91.1409, 29.6456, 91.139370663514, 29.648336012634, "一级"),
    (18, "优纳特演示成交单位36", "农业检测", "西藏自治区", "日喀则市", "桑珠孜区", "540200", 88.8851, 29.2675, 88.883068666554, 29.270768421569, "三级"),
    (19, "优纳特演示成交单位37", "材料分析", "甘肃省", "兰州市", "城关区", "620100", 103.8343, 36.0611, 103.831896890861, 36.061427282794, "一级"),
    (20, "优纳特演示成交单位38", "环境监测", "甘肃省", "天水市", "秦州区", "620500", 105.7249, 34.5809, 105.720963089870, 34.582217961355, "二级"),
    (21, "优纳特演示成交单位39", "高原科研", "青海省", "西宁市", "城西区", "630100", 101.7658, 36.6283, 101.763851712142, 36.628365542539, "一级"),
    (22, "优纳特演示成交单位40", "食品安全", "青海省", "海东市", "平安区", "630200", 102.1043, 36.5029, 102.102230099533, 36.502835386291, "三级"),
    (23, "优纳特演示成交单位41", "能源化工", "宁夏回族自治区", "银川市", "金凤区", "640100", 106.2426, 38.4731, 106.238206446703, 38.472647969552, "一级"),
    (24, "优纳特演示成交单位42", "农业检测", "宁夏回族自治区", "吴忠市", "利通区", "640300", 106.1984, 37.9976, 106.194000973107, 37.997056633479, "二级"),
    (25, "优纳特演示成交单位43", "食品安全", "新疆维吾尔自治区", "乌鲁木齐市", "水磨沟区", "650100", 87.6425, 43.8321, 87.639608908015, 43.830866863345, "一级"),
    (26, "优纳特演示成交单位44", "农业检测", "新疆维吾尔自治区", "昌吉回族自治州", "昌吉市", "652300", 87.3082, 44.0112, 87.305088875877, 44.009883189990, "二级"),
)

EXTRA_PROJECT_DATES = (
    (2, date(2024, 1, 22)), (3, date(2024, 3, 10)),
    (1, date(2024, 4, 18)), (3, date(2024, 6, 7)),
    (1, date(2024, 7, 23)), (2, date(2024, 9, 5)),
    (1, date(2024, 10, 14)), (2, date(2024, 12, 2)),
    (1, date(2025, 2, 8)), (2, date(2025, 3, 19)), (1, date(2025, 11, 6)),
    (1, date(2026, 7, 15)), (2, date(2026, 8, 12)),
)


def _project_amount(customer_number: int, year: int) -> Decimal:
    """生成有年度增长且不同单位梯度明显的虚构合同金额。"""

    base = Decimal(180_000 + customer_number * 31_000 + customer_number % 4 * 70_000)
    return (base * {2024: Decimal("0.82"), 2025: Decimal("1.00"), 2026: Decimal("1.16")}[year]).quantize(Decimal("0.01"))


def _base_project_date(customer_number: int, year: int) -> date:
    """把三年基础项目稳定分散到各季度，且不生成当前日期之后的成交。"""

    if year == 2024:
        quarter = (customer_number - 1) % 4 + 1
    elif year == 2025:
        quarter = customer_number % 4 + 1
    else:
        quarter = (customer_number - 1) % 3 + 1
    month = (quarter - 1) * 3 + 1 + customer_number % 3
    if year == 2026 and quarter == 3:
        month = 7 + customer_number % 2
    return date(year, month, 6 + customer_number * 2 % 19)


def _build_project_rows() -> list[dict[str, object]]:
    """生成三年基础成交和少量复购项目，使每个历史季度均有至少十条全国数据。"""

    rows: list[dict[str, object]] = []
    project_number = 0
    year_labels = {2024: "基础设备一期", 2025: "分析平台升级", 2026: "智能检测扩容"}
    for year in (2024, 2025, 2026):
        for customer_number, name, *_rest in CUSTOMERS:
            project_number += 1
            rows.append({
                "id": _uuid(23400 + project_number),
                "organization_id": _uuid(23000 + customer_number),
                "opportunity_id": _uuid(23300 + customer_number) if year == 2025 else None,
                "salesperson_id": _uuid(8001 + (customer_number - 1) % 6),
                "name": f"{name}{year}年{year_labels[year]}演示项目",
                "contract_amount": _project_amount(customer_number, year),
                "signed_at": _base_project_date(customer_number, year),
                "project_detail": "纯虚构演示成交，仅用于全国数据洞察的年度、季度和省市统计",
            })
    for extra_number, (customer_number, signed_at) in enumerate(EXTRA_PROJECT_DATES, start=1):
        project_number += 1
        name = CUSTOMERS[customer_number - 1][1]
        rows.append({
            "id": _uuid(23400 + project_number),
            "organization_id": _uuid(23000 + customer_number),
            "opportunity_id": None,
            "salesperson_id": _uuid(8001 + (customer_number - 1) % 6),
            "name": f"{name}{signed_at.year}年第{extra_number:02d}个复购演示项目",
            "contract_amount": Decimal(150_000 + extra_number * 23_000),
            "signed_at": signed_at,
            "project_detail": "纯虚构复购成交，用于补足季度排名所需的最小样本",
        })
    return rows


def _build_opportunity_rows() -> list[dict[str, object]]:
    """为每家演示单位生成一个当前商机和一个已关联成交的历史商机。"""

    stages = ("已识别", "资格确认", "方案/报价", "商务谈判")
    rows: list[dict[str, object]] = []
    for customer_number, name, *_rest in CUSTOMERS:
        salesperson_id = _uuid(8001 + (customer_number - 1) % 6)
        rows.extend((
            {
                "id": _uuid(23200 + customer_number),
                "organization_id": _uuid(23000 + customer_number),
                "salesperson_id": salesperson_id,
                "title": f"{name}后续采购演示商机",
                "stage": stages[(customer_number - 1) % len(stages)],
                "estimated_amount": Decimal(320_000 + customer_number * 55_000 + customer_number % 5 * 90_000),
                "ai_summary": "纯虚构活跃商机，仅用于数据洞察的当前储备与阶段分布",
                "next_action": "演示下一步：确认预算、方案范围和采购排期",
                "next_action_at": date(2026, 9 + customer_number % 4, 5 + customer_number % 20),
            },
            {
                "id": _uuid(23300 + customer_number),
                "organization_id": _uuid(23000 + customer_number),
                "salesperson_id": salesperson_id,
                "title": f"{name}2025年已转化演示商机",
                "stage": "商务谈判",
                "estimated_amount": _project_amount(customer_number, 2025),
                "ai_summary": "纯虚构历史商机，已由关联成交项目转化，不计入当前储备",
                "next_action": "演示历史动作：完成合同签署并转入交付",
                "next_action_at": _base_project_date(customer_number, 2025),
            },
        ))
    return rows


def _validate_demo_data() -> None:
    """在写库前锁定全国缺口、时间范围和最小季度样本，避免演示数据静默退化。"""

    expected_provinces = {
        "北京市", "上海市", "天津市", "山西省", "内蒙古自治区", "黑龙江省", "海南省",
        "贵州省", "西藏自治区", "甘肃省", "青海省", "宁夏回族自治区", "新疆维吾尔自治区",
    }
    project_rows = _build_project_rows()
    opportunity_rows = _build_opportunity_rows()
    quarter_counts = Counter(
        (row["signed_at"].year, (row["signed_at"].month - 1) // 3 + 1)
        for row in project_rows
    )
    assert len(CUSTOMERS) == 26
    assert {row[3] for row in CUSTOMERS} == expected_provinces
    assert len(project_rows) == 91
    assert len(opportunity_rows) == 52
    assert Counter(row["signed_at"].year for row in project_rows) == Counter({2024: 34, 2025: 29, 2026: 28})
    assert quarter_counts == Counter({
        (2024, 1): 9, (2024, 2): 9, (2024, 3): 8, (2024, 4): 8,
        (2025, 1): 8, (2025, 2): 7, (2025, 3): 7, (2025, 4): 7,
        (2026, 1): 9, (2026, 2): 9, (2026, 3): 10,
    })
    assert sum(row["opportunity_id"] is not None for row in project_rows) == len(CUSTOMERS)
    assert all(row["contract_amount"] > 0 for row in project_rows)
    assert max(row["signed_at"] for row in project_rows) <= date(2026, 8, 25)
    assert all(name.startswith("优纳特演示成交单位") for _number, name, *_rest in CUSTOMERS)


def upgrade() -> None:
    """写入缺失十三省的虚构单位、三年成交及当前/已转化商机。"""

    _validate_demo_data()
    organization_table = sa.table(
        "organization",
        *[sa.column(name) for name in (
            "id", "name", "normalized_name", "organization_type", "industry", "customer_status",
            "review_status", "inclusion_reason", "is_sports_exception", "recent_follow_up_at",
            "recent_follow_up_content", "follow_up_owner", "cooperation_intent", "cooperation_level", "notes",
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
    opportunity_table = sa.table(
        "opportunity",
        *[sa.column(name) for name in (
            "id", "organization_id", "salesperson_id", "title", "stage", "estimated_amount", "ai_summary",
            "next_action", "next_action_at",
        )],
    )
    project_table = sa.table(
        "sales_project",
        *[sa.column(name) for name in (
            "id", "organization_id", "opportunity_id", "salesperson_id", "name", "contract_amount",
            "signed_at", "project_detail",
        )],
    )
    now = datetime(2026, 8, 25, 11, tzinfo=UTC)

    op.bulk_insert(organization_table, [{
        "id": _uuid(23000 + number),
        "name": name,
        "normalized_name": name.lower(),
        "organization_type": "企业",
        "industry": industry,
        "customer_status": "已成交客户",
        "review_status": "已核验",
        "inclusion_reason": "优纳特全国销售数据洞察虚构演示数据",
        "is_sports_exception": False,
        "recent_follow_up_at": now,
        "recent_follow_up_content": "演示跟进：已完成历史项目并持续推进后续采购",
        "follow_up_owner": f"演示销售{(number - 1) % 6 + 1}",
        "cooperation_intent": "演示合作：保持复购并推进下一阶段方案",
        "cooperation_level": cooperation_level,
        "attributes": {"demo": True, "data_insights_demo": True},
        "notes": "纯虚构单位，仅用于优纳特全国销售数据洞察演示",
    } for number, name, industry, _province, _city, _district, _adcode, _longitude, _latitude, _wgs_longitude, _wgs_latitude, cooperation_level in CUSTOMERS])

    op.bulk_insert(site_table, [{
        "id": _uuid(23100 + number),
        "organization_id": _uuid(23000 + number),
        "site_name": f"{name}演示主地点",
        "raw_address": f"{city}{district}演示科创园{number}号",
        "address": f"{city}{district}演示科创园{number}号",
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
            sa.text("UPDATE organization_site SET location = ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326) WHERE id = :site_id"),
            {"site_id": _uuid(23100 + number), "longitude": wgs_longitude, "latitude": wgs_latitude},
        )

    op.bulk_insert(opportunity_table, _build_opportunity_rows())
    op.bulk_insert(project_table, _build_project_rows())


def downgrade() -> None:
    """删除本迁移的虚构单位，并依靠级联清理其地点、商机和成交项目。"""

    op.execute(sa.text("DELETE FROM organization WHERE id BETWEEN :first_id AND :last_id").bindparams(
        first_id=_uuid(23001), last_id=_uuid(23000 + len(CUSTOMERS)),
    ))
