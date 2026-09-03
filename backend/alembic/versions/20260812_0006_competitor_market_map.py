"""创建同行市场独立数据域、正式单位关联及明确标记的虚构演示数据。"""

from datetime import UTC, date, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260812_0006"
down_revision = "20260812_0005"
branch_labels = None
depends_on = None

intelligence_source_type = postgresql.ENUM("公开信息", "一线反馈", "推测", name="intelligence_source_type", create_type=False)
intelligence_confidence = postgresql.ENUM("高", "中", "低", name="intelligence_confidence", create_type=False)
competitor_site_type = postgresql.ENUM("总部", "分部", "服务点", name="competitor_site_type", create_type=False)
competitor_strength_level = postgresql.ENUM("强", "中", "弱", name="competitor_strength_level", create_type=False)
competitor_region_level = postgresql.ENUM("省", "市", name="competitor_region_level", create_type=False)
competitor_customer_level = postgresql.ENUM("一级", "二级", "三级", name="competitor_customer_level", create_type=False)
competitor_match_status = postgresql.ENUM("待确认", "已确认", "已拒绝", name="competitor_match_status", create_type=False)


def _uuid(number: int) -> str:
    """生成迁移内稳定 UUID，保证演示关联可重复创建和清理。"""

    return f"00000000-0000-4000-8000-{number:012d}"


def upgrade() -> None:
    """创建同行表、写入十组虚构数据，并把三个演示公司确认关联到正式单位。"""

    bind = op.get_bind()
    for enum_type in (
        intelligence_source_type,
        intelligence_confidence,
        competitor_site_type,
        competitor_strength_level,
        competitor_region_level,
        competitor_customer_level,
        competitor_match_status,
    ):
        enum_type.create(bind, checkfirst=True)

    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE organization_type ADD VALUE IF NOT EXISTS '企业'")

    op.create_table(
        "competitor",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("color ~ '^#[0-9A-Fa-f]{6}$'", name="ck_competitor_color_hex"),
    )
    op.create_table(
        "competitor_site",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("competitor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("competitor.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("site_type", competitor_site_type, nullable=False),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("province", sa.String(60), nullable=False),
        sa.Column("city", sa.String(60), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("source_type", intelligence_source_type, nullable=False),
        sa.Column("source_reference", sa.String(500), nullable=False),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("confidence", intelligence_confidence, nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("competitor_id", "name", name="uq_competitor_site_name"),
        sa.CheckConstraint("longitude BETWEEN 72.004 AND 137.8347 AND latitude BETWEEN 0.8293 AND 55.8271", name="ck_competitor_site_gcj02_bounds"),
    )
    op.create_index("ix_competitor_site_competitor_id", "competitor_site", ["competitor_id"])
    op.create_index("uq_competitor_single_primary_site", "competitor_site", ["competitor_id"], unique=True, postgresql_where=sa.text("is_primary"))
    op.create_table(
        "competitor_customer",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("competitor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("competitor.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("customer_level", competitor_customer_level, nullable=False),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("province", sa.String(60), nullable=False),
        sa.Column("city", sa.String(60), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("source_type", intelligence_source_type, nullable=False),
        sa.Column("source_reference", sa.String(500), nullable=False),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("confidence", intelligence_confidence, nullable=False),
        sa.Column("first_observed_at", sa.Date()),
        sa.Column("last_verified_at", sa.Date()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("competitor_id", "name", name="uq_competitor_customer_name"),
        sa.CheckConstraint("longitude BETWEEN 72.004 AND 137.8347 AND latitude BETWEEN 0.8293 AND 55.8271", name="ck_competitor_customer_gcj02_bounds"),
    )
    op.create_index("ix_competitor_customer_competitor_id", "competitor_customer", ["competitor_id"])
    op.create_table(
        "competitor_deal",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("competitor_customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("competitor_customer.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_name", sa.String(255), nullable=False),
        sa.Column("deal_type", sa.String(80), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("signed_at", sa.Date()),
        sa.Column("source_type", intelligence_source_type, nullable=False),
        sa.Column("source_reference", sa.String(500), nullable=False),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("confidence", intelligence_confidence, nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount > 0", name="ck_competitor_deal_positive_amount"),
    )
    op.create_index("ix_competitor_deal_customer_id", "competitor_deal", ["competitor_customer_id"])
    op.create_table(
        "competitor_strength_region",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("competitor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("competitor.id", ondelete="CASCADE"), nullable=False),
        sa.Column("region_level", competitor_region_level, nullable=False),
        sa.Column("province", sa.String(60), nullable=False),
        sa.Column("city", sa.String(60)),
        sa.Column("strength_level", competitor_strength_level, nullable=False),
        sa.Column("source_type", intelligence_source_type, nullable=False),
        sa.Column("source_reference", sa.String(500), nullable=False),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("confidence", intelligence_confidence, nullable=False),
        sa.Column("basis", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("competitor_id", "province", "city", name="uq_competitor_strength_region"),
        sa.CheckConstraint("(region_level = '省' AND city IS NULL) OR (region_level = '市' AND city IS NOT NULL)", name="ck_competitor_strength_region_scope"),
    )
    op.create_index("ix_competitor_strength_region_competitor_id", "competitor_strength_region", ["competitor_id"])
    op.create_table(
        "competitor_customer_organization_link",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("competitor_customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("competitor_customer.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_status", competitor_match_status, nullable=False),
        sa.Column("match_method", sa.String(120), nullable=False),
        sa.Column("match_confidence", intelligence_confidence, nullable=False),
        sa.Column("matched_by", sa.String(120)),
        sa.Column("matched_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_competitor_link_organization_id", "competitor_customer_organization_link", ["organization_id"])

    competitor_table = sa.table("competitor", sa.column("id"), sa.column("name"), sa.column("color"), sa.column("description"), sa.column("is_active"))
    site_table = sa.table("competitor_site", *[sa.column(name) for name in ("id", "competitor_id", "name", "site_type", "address", "province", "city", "longitude", "latitude", "source_type", "source_reference", "source_url", "confidence", "notes", "is_primary")])
    customer_table = sa.table("competitor_customer", *[sa.column(name) for name in ("id", "competitor_id", "name", "customer_level", "address", "province", "city", "longitude", "latitude", "source_type", "source_reference", "source_url", "confidence", "first_observed_at", "last_verified_at", "notes")])
    deal_table = sa.table("competitor_deal", *[sa.column(name) for name in ("id", "competitor_customer_id", "project_name", "deal_type", "amount", "signed_at", "source_type", "source_reference", "source_url", "confidence", "notes")])
    region_table = sa.table("competitor_strength_region", *[sa.column(name) for name in ("id", "competitor_id", "region_level", "province", "city", "strength_level", "source_type", "source_reference", "source_url", "confidence", "basis")])

    competitors = [
        (1, "同行1", "#147D64", "华东市场型同行（演示）"),
        (2, "同行2", "#D7652D", "北方渠道型同行（演示）"),
        (3, "同行3", "#3D6FB4", "华南服务型同行（演示）"),
        (4, "同行4", "#7A5AB4", "西南项目型同行（演示）"),
        (5, "同行5", "#B78A20", "华中区域型同行（演示）"),
        (6, "同行6", "#238A9D", "长三角技术型同行（演示）"),
        (7, "同行7", "#A24C64", "西北覆盖型同行（演示）"),
        (8, "同行8", "#526D35", "东北服务型同行（演示）"),
        (9, "同行9", "#8A5638", "环渤海项目型同行（演示）"),
        (10, "同行10", "#4D657D", "东南渠道型同行（演示）"),
    ]
    op.bulk_insert(competitor_table, [{"id": _uuid(600 + index), "name": name, "color": color, "description": description, "is_active": True} for index, name, color, description in competitors])

    cities = [
        ("上海市", "上海市", 121.4737, 31.2304), ("北京市", "北京市", 116.4074, 39.9042),
        ("广东省", "广州市", 113.2644, 23.1291), ("四川省", "成都市", 104.0665, 30.5723),
        ("湖北省", "武汉市", 114.3054, 30.5931), ("江苏省", "南京市", 118.7969, 32.0603),
        ("陕西省", "西安市", 108.9398, 34.3416), ("辽宁省", "沈阳市", 123.4315, 41.8057),
        ("山东省", "济南市", 117.1201, 36.6512), ("浙江省", "杭州市", 120.1551, 30.2741),
        ("福建省", "厦门市", 118.0894, 24.4798), ("河南省", "郑州市", 113.6254, 34.7466),
        ("湖南省", "长沙市", 112.9388, 28.2282), ("重庆市", "重庆市", 106.5516, 29.5630),
        ("安徽省", "合肥市", 117.2272, 31.8206), ("河北省", "石家庄市", 114.5149, 38.0428),
        ("吉林省", "长春市", 125.3235, 43.8171), ("广西壮族自治区", "南宁市", 108.3669, 22.8170),
    ]
    source_types = ["公开信息", "一线反馈", "推测"]
    confidences = ["高", "中", "低"]
    site_rows: list[dict[str, object]] = []
    extra_sites = {1: [(10, "服务点")], 2: [(15, "分部")], 4: [(12, "服务点")], 6: [(9, "分部"), (14, "服务点")], 8: [(16, "服务点")], 10: [(2, "分部")]}
    site_sequence = 700
    for competitor_number, name, _color, _description in competitors:
        province, city, longitude, latitude = cities[competitor_number - 1]
        site_sequence += 1
        site_rows.append({"id": _uuid(site_sequence), "competitor_id": _uuid(600 + competitor_number), "name": f"{name}总部", "site_type": "总部", "address": f"{city}演示总部地址", "province": province, "city": city, "longitude": longitude, "latitude": latitude, "source_type": "公开信息", "source_reference": "演示数据：企业官网新闻样例", "source_url": None, "confidence": "高", "notes": "纯虚构同行据点", "is_primary": True})
        for city_index, site_type in extra_sites.get(competitor_number, []):
            province, city, longitude, latitude = cities[city_index]
            site_sequence += 1
            site_rows.append({"id": _uuid(site_sequence), "competitor_id": _uuid(600 + competitor_number), "name": f"{name}{city}{site_type}", "site_type": site_type, "address": f"{city}演示{site_type}地址", "province": province, "city": city, "longitude": longitude + 0.03, "latitude": latitude + 0.02, "source_type": "一线反馈", "source_reference": "演示数据：销售上报样例", "source_url": None, "confidence": "中", "notes": "纯虚构同行据点", "is_primary": False})
    op.bulk_insert(site_table, site_rows)

    customer_rows: list[dict[str, object]] = []
    deal_rows: list[dict[str, object]] = []
    linked_customers: list[tuple[str, str]] = []
    customer_sequence = 2000
    deal_sequence = 3000
    linked_names = {1: "公司1", 2: "公司2", 3: "公司3"}
    deal_types = ["设备采购", "耗材供应", "技术服务"]
    customer_levels = ["一级", "二级", "三级"]
    for competitor_number, name, _color, _description in competitors:
        for unit_number in range(1, 7):
            customer_sequence += 1
            city_index = ((competitor_number - 1) * 3 + unit_number - 1) % len(cities)
            province, city, longitude, latitude = cities[city_index]
            customer_name = linked_names[competitor_number] if unit_number == 1 and competitor_number in linked_names else f"{name}签约单位{unit_number}"
            source_index = (competitor_number + unit_number) % 3
            customer_rows.append({"id": _uuid(customer_sequence), "competitor_id": _uuid(600 + competitor_number), "name": customer_name, "customer_level": customer_levels[(unit_number - 1) % 3], "address": f"{city}演示成交单位地址{unit_number}", "province": province, "city": city, "longitude": longitude + unit_number * 0.008, "latitude": latitude - unit_number * 0.006, "source_type": source_types[source_index], "source_reference": f"演示数据：{source_types[source_index]}样例", "source_url": None, "confidence": confidences[source_index], "first_observed_at": date(2025, (unit_number % 12) + 1, min(10 + competitor_number, 28)), "last_verified_at": date(2026, ((competitor_number + unit_number) % 7) + 1, 12), "notes": "纯虚构同行成交单位"})
            if unit_number == 1 and competitor_number in linked_names:
                linked_customers.append((_uuid(customer_sequence), customer_name))
            deal_sequence += 1
            deal_rows.append({"id": _uuid(deal_sequence), "competitor_customer_id": _uuid(customer_sequence), "project_name": f"{customer_name}{deal_types[(unit_number - 1) % 3]}项目", "deal_type": deal_types[(unit_number - 1) % 3], "amount": 180000 + competitor_number * 37000 + unit_number * 29000, "signed_at": date(2025 + (unit_number % 2), ((competitor_number + unit_number) % 12) + 1, min(8 + unit_number, 28)), "source_type": source_types[source_index], "source_reference": f"演示数据：{source_types[source_index]}成交样例", "source_url": None, "confidence": confidences[source_index], "notes": "纯虚构交易金额"})
    op.bulk_insert(customer_table, customer_rows)
    op.bulk_insert(deal_table, deal_rows)

    region_rows: list[dict[str, object]] = []
    region_sequence = 4000
    for competitor_number, name, _color, _description in competitors:
        region_city_indexes = [competitor_number - 1, (competitor_number + 4) % len(cities), (competitor_number + 9) % len(cities)]
        for level_index, city_index in enumerate(region_city_indexes):
            region_sequence += 1
            province, city, _longitude, _latitude = cities[city_index]
            strength = ["强", "中", "弱"][level_index]
            region_rows.append({"id": _uuid(region_sequence), "competitor_id": _uuid(600 + competitor_number), "region_level": "省" if level_index == 0 else "市", "province": province, "city": None if level_index == 0 else city, "strength_level": strength, "source_type": source_types[level_index], "source_reference": f"演示数据：{source_types[level_index]}区域判断样例", "source_url": None, "confidence": confidences[level_index], "basis": f"根据{name}虚构成交分布与据点覆盖，标记为{strength}势区域。"})
    op.bulk_insert(region_table, region_rows)

    organization_table = sa.table(
        "organization",
        *[
            sa.column(name)
            for name in (
                "id",
                "name",
                "normalized_name",
                "organization_type",
                "industry",
                "customer_status",
                "review_status",
                "inclusion_reason",
                "is_sports_exception",
            )
        ],
        sa.column("attributes", postgresql.JSONB()),
        sa.column("notes"),
    )
    organization_site_table = sa.table("organization_site", *[sa.column(name) for name in ("id", "organization_id", "site_name", "raw_address", "address", "province", "city", "district", "geocode_status", "geocode_confidence", "longitude", "latitude", "is_primary")])
    link_table = sa.table("competitor_customer_organization_link", *[sa.column(name) for name in ("id", "competitor_customer_id", "organization_id", "match_status", "match_method", "match_confidence", "matched_by", "matched_at", "notes")])
    organization_rows: list[dict[str, object]] = []
    organization_site_rows: list[dict[str, object]] = []
    link_rows: list[dict[str, object]] = []
    for index, (customer_id, company_name) in enumerate(linked_customers, start=1):
        province, city, longitude, latitude = cities[(index - 1) * 3]
        organization_id = _uuid(5000 + index)
        organization_rows.append({"id": organization_id, "name": company_name, "normalized_name": company_name.lower(), "organization_type": "企业", "industry": "演示行业", "customer_status": "潜在客户", "review_status": "已核验", "inclusion_reason": "同行签约关联功能演示", "is_sports_exception": False, "attributes": {"demo": True}, "notes": "纯虚构单位，仅用于同行关联演示"})
        organization_site_rows.append({"id": _uuid(5100 + index), "organization_id": organization_id, "site_name": f"{company_name}主地点", "raw_address": f"{city}演示地址", "address": f"{city}演示地址", "province": province, "city": city, "district": None, "geocode_status": "已定位", "geocode_confidence": 100, "longitude": longitude + 0.008, "latitude": latitude - 0.006, "is_primary": True})
        link_rows.append({"id": _uuid(5200 + index), "competitor_customer_id": customer_id, "organization_id": organization_id, "match_status": "已确认", "match_method": "名称与地址人工确认", "match_confidence": "高", "matched_by": "演示迁移", "matched_at": datetime(2026, 8, 12, tzinfo=UTC), "notes": "纯虚构关联，用于验证单位数据库展示"})
    op.bulk_insert(organization_table, organization_rows)
    op.bulk_insert(organization_site_table, organization_site_rows)
    op.bulk_insert(link_table, link_rows)


def downgrade() -> None:
    """移除同行数据域和三个演示单位，并恢复原 organization_type 枚举。"""

    op.execute("DELETE FROM organization WHERE id IN ('00000000-0000-4000-8000-000000005001', '00000000-0000-4000-8000-000000005002', '00000000-0000-4000-8000-000000005003')")
    for table in ("competitor_customer_organization_link", "competitor_strength_region", "competitor_deal", "competitor_customer", "competitor_site", "competitor"):
        op.drop_table(table)
    for enum_type in (competitor_match_status, competitor_customer_level, competitor_region_level, competitor_strength_level, competitor_site_type, intelligence_confidence, intelligence_source_type):
        enum_type.drop(op.get_bind(), checkfirst=True)
    op.execute("ALTER TYPE organization_type RENAME TO organization_type_with_enterprise")
    op.execute("CREATE TYPE organization_type AS ENUM ('高校', '研究院', '疾控', '食药', '环保', '公安')")
    op.execute("ALTER TABLE organization ALTER COLUMN organization_type TYPE organization_type USING organization_type::text::organization_type")
    op.execute("DROP TYPE organization_type_with_enterprise")
