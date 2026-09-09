"""创建销售人员覆盖与活动数据域，并写入稳定的虚构演示数据。"""

from datetime import UTC, date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260813_0010"
down_revision = "20260813_0009"
branch_labels = None
depends_on = None

sales_activity_type = postgresql.ENUM("拜访", "演示", "市场活动", name="sales_activity_type", create_type=False)


def _uuid(number: int) -> str:
    """生成迁移内稳定 UUID，保证虚构演示数据可验证和回滚。"""

    return f"00000000-0000-4000-8000-{number:012d}"


SALESPERSONS = (
    (1, "DEMO-S001", "张1", "#E76F51"),
    (2, "DEMO-S002", "王3", "#2A9D8F"),
    (3, "DEMO-S003", "冯7", "#457B9D"),
    (4, "DEMO-S004", "李2", "#8A5CF6"),
    (5, "DEMO-S005", "赵6", "#D4A72C"),
    (6, "DEMO-S006", "陈4", "#D95D8F"),
)

COVERAGE_BY_SALESPERSON = {
    1: (
        ("江苏省", "南京市", "320100"),
        ("江苏省", "无锡市", "320200"),
        ("江苏省", "常州市", "320400"),
        ("江苏省", "苏州市", "320500"),
        ("江苏省", "盐城市", "320900"),
        ("浙江省", "杭州市", "330100"),
    ),
    2: (
        ("辽宁省", "沈阳市", "210100"),
        ("辽宁省", "大连市", "210200"),
        ("吉林省", "长春市", "220100"),
        ("吉林省", "吉林市", "220200"),
        ("黑龙江省", "哈尔滨市", "230100"),
    ),
    3: (
        ("广东省", "广州市", "440100"),
        ("广东省", "深圳市", "440300"),
        ("广东省", "佛山市", "440600"),
        ("广东省", "湛江市", "440800"),
        ("广东省", "东莞市", "441900"),
    ),
    4: (
        ("重庆市", "重庆市", "500000"),
        ("四川省", "成都市", "510100"),
        ("贵州省", "贵阳市", "520100"),
        ("云南省", "昆明市", "530100"),
    ),
    5: (
        ("河南省", "郑州市", "410100"),
        ("湖北省", "武汉市", "420100"),
        ("湖南省", "长沙市", "430100"),
        ("江西省", "南昌市", "360100"),
        ("广西壮族自治区", "柳州市", "450200"),
    ),
    6: (
        ("浙江省", "杭州市", "330100"),
        ("浙江省", "宁波市", "330200"),
        ("浙江省", "温州市", "330300"),
        ("浙江省", "金华市", "330700"),
        ("安徽省", "合肥市", "340100"),
    ),
}

ACTIVITY_DATES = (
    datetime(2026, 8, 8, 9, tzinfo=UTC),
    datetime(2026, 7, 24, 9, tzinfo=UTC),
    datetime(2026, 6, 18, 9, tzinfo=UTC),
    datetime(2026, 5, 26, 9, tzinfo=UTC),
    datetime(2026, 4, 14, 9, tzinfo=UTC),
    datetime(2026, 3, 9, 9, tzinfo=UTC),
    datetime(2026, 1, 20, 9, tzinfo=UTC),
    datetime(2025, 11, 16, 9, tzinfo=UTC),
    datetime(2025, 9, 11, 9, tzinfo=UTC),
)

ORGANIZATION_BY_SALESPERSON = {1: 1, 2: 2, 3: 3, 4: 4, 5: 6, 6: 5}

OPPORTUNITIES = (
    (1, 1, 1, "公司1实验室扩容项目", "方案/报价", "410000.00", date(2026, 9, 3)),
    (2, 2, 2, "公司2检测平台升级", "商务谈判", "560000.00", date(2026, 8, 28)),
    (3, 3, 3, "公司3移动监测项目", "资格确认", "320000.00", date(2026, 10, 12)),
    (4, 4, 4, "公司4自动化前处理二期", "方案/报价", "690000.00", date(2026, 9, 18)),
    (5, 6, 5, "公司6材料分析升级", "已识别", "270000.00", date(2026, 11, 6)),
    (6, 5, 6, "公司5研发平台二期", "商务谈判", "880000.00", date(2026, 8, 25)),
    (7, 1, 1, "公司1历史预算项目", "已关闭失单", "180000.00", None),
    (8, 2, 2, "公司2历史扩建项目", "已关闭失单", "240000.00", None),
    (9, 3, 3, "公司3历史运维项目", "已关闭失单", "150000.00", None),
    (10, 4, 4, "公司4历史研发项目", "已关闭失单", "210000.00", None),
    (11, 6, 5, "公司6历史产线项目", "已关闭失单", "360000.00", None),
    (12, 5, 6, "公司5历史服务项目", "已关闭失单", "190000.00", None),
)

PROJECT_SALESPERSONS = (
    (1, 1),
    (2, 1),
    (3, 2),
    (4, 3),
    (5, 3),
    (6, 4),
    (7, 6),
    (8, 6),
    (9, 5),
)


def _build_coverage_rows() -> list[dict[str, object]]:
    """把销售与城市配置展开为可批量写入的当前覆盖记录。"""

    rows: list[dict[str, object]] = []
    sequence = 8100
    for salesperson_number, cities in COVERAGE_BY_SALESPERSON.items():
        for province, city, adcode in cities:
            sequence += 1
            rows.append({
                "id": _uuid(sequence),
                "salesperson_id": _uuid(8000 + salesperson_number),
                "province": province,
                "city": city,
                "amap_adcode": adcode,
            })
    return rows


def _build_activity_rows() -> list[dict[str, object]]:
    """生成覆盖四档时间范围的虚构活动，确保月份切换存在可比较差异。"""

    activity_types = ("拜访", "演示", "市场活动")
    rows: list[dict[str, object]] = []
    sequence = 9000
    for salesperson_number, cities in COVERAGE_BY_SALESPERSON.items():
        organization_number = ORGANIZATION_BY_SALESPERSON[salesperson_number]
        for date_index, occurred_at in enumerate(ACTIVITY_DATES):
            event_count = 1 + ((salesperson_number + date_index) % 3)
            for event_index in range(event_count):
                sequence += 1
                province, city, adcode = cities[(salesperson_number + date_index + event_index) % len(cities)]
                rows.append({
                    "id": _uuid(sequence),
                    "salesperson_id": _uuid(8000 + salesperson_number),
                    "organization_id": _uuid(5000 + organization_number) if event_index == 0 else None,
                    "activity_type": activity_types[(salesperson_number + date_index + event_index) % len(activity_types)],
                    "occurred_at": occurred_at.replace(hour=9 + event_index),
                    "province": province,
                    "city": city,
                    "amap_adcode": adcode,
                    "notes": "纯虚构销售活动，仅用于销售覆盖与人效地图演示",
                })
    return rows


def upgrade() -> None:
    """创建销售数据域、补充业绩归属，并填充可覆盖 1/3/6/12 月的演示数据。"""

    bind = op.get_bind()
    sales_activity_type.create(bind, checkfirst=True)

    op.create_table(
        "salesperson",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_code", sa.String(40), nullable=False, unique=True),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("color ~ '^#[0-9A-Fa-f]{6}$'", name="ck_salesperson_color_hex"),
    )
    op.create_table(
        "salesperson_coverage_city",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("salesperson_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("salesperson.id", ondelete="CASCADE"), nullable=False),
        sa.Column("province", sa.String(60), nullable=False),
        sa.Column("city", sa.String(60), nullable=False),
        sa.Column("amap_adcode", sa.String(12), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("salesperson_id", "amap_adcode", name="uq_salesperson_coverage_city"),
        sa.CheckConstraint("amap_adcode ~ '^[0-9]{6}$'", name="ck_salesperson_coverage_city_adcode"),
    )
    op.create_index("ix_salesperson_coverage_city_adcode", "salesperson_coverage_city", ["amap_adcode"])

    op.add_column("opportunity", sa.Column("salesperson_id", postgresql.UUID(as_uuid=True)))
    op.create_foreign_key("fk_opportunity_salesperson_id_salesperson", "opportunity", "salesperson", ["salesperson_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_opportunity_salesperson_stage", "opportunity", ["salesperson_id", "stage"])
    op.add_column("sales_project", sa.Column("salesperson_id", postgresql.UUID(as_uuid=True)))
    op.create_foreign_key("fk_sales_project_salesperson_id_salesperson", "sales_project", "salesperson", ["salesperson_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_sales_project_salesperson_signed_at", "sales_project", ["salesperson_id", "signed_at"])

    op.create_table(
        "sales_activity",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("salesperson_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("salesperson.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id", ondelete="SET NULL")),
        sa.Column("activity_type", sales_activity_type, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("province", sa.String(60), nullable=False),
        sa.Column("city", sa.String(60), nullable=False),
        sa.Column("amap_adcode", sa.String(12), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amap_adcode ~ '^[0-9]{6}$'", name="ck_sales_activity_adcode"),
    )
    op.create_index("ix_sales_activity_salesperson_occurred_at", "sales_activity", ["salesperson_id", "occurred_at"])
    op.create_index("ix_sales_activity_adcode_occurred_at", "sales_activity", ["amap_adcode", "occurred_at"])

    salesperson_table = sa.table("salesperson", *[sa.column(name) for name in ("id", "employee_code", "display_name", "color", "is_active")])
    coverage_table = sa.table("salesperson_coverage_city", *[sa.column(name) for name in ("id", "salesperson_id", "province", "city", "amap_adcode")])
    activity_table = sa.table("sales_activity", *[sa.column(name) for name in ("id", "salesperson_id", "organization_id", "activity_type", "occurred_at", "province", "city", "amap_adcode", "notes")])
    opportunity_table = sa.table("opportunity", *[sa.column(name) for name in ("id", "organization_id", "salesperson_id", "title", "stage", "estimated_amount", "ai_summary", "next_action", "next_action_at")])

    op.bulk_insert(salesperson_table, [{
        "id": _uuid(8000 + number),
        "employee_code": employee_code,
        "display_name": display_name,
        "color": color,
        "is_active": True,
    } for number, employee_code, display_name, color in SALESPERSONS])
    op.bulk_insert(coverage_table, _build_coverage_rows())
    op.bulk_insert(activity_table, _build_activity_rows())
    op.bulk_insert(opportunity_table, [{
        "id": _uuid(10000 + number),
        "organization_id": _uuid(5000 + organization_number),
        "salesperson_id": _uuid(8000 + salesperson_number),
        "title": title,
        "stage": stage,
        "estimated_amount": Decimal(amount),
        "ai_summary": "纯虚构储备项目，仅用于销售覆盖与人效地图演示",
        "next_action": "演示下一步：确认预算与技术范围" if stage != "已关闭失单" else None,
        "next_action_at": next_action_at,
    } for number, organization_number, salesperson_number, title, stage, amount, next_action_at in OPPORTUNITIES])

    connection = op.get_bind()
    for project_number, salesperson_number in PROJECT_SALESPERSONS:
        connection.execute(
            sa.text("UPDATE sales_project SET salesperson_id = :salesperson_id WHERE id = :project_id"),
            {"salesperson_id": _uuid(8000 + salesperson_number), "project_id": _uuid(5300 + project_number)},
        )
    for salesperson_number, _employee_code, display_name, _color in SALESPERSONS:
        organization_number = ORGANIZATION_BY_SALESPERSON[salesperson_number]
        connection.execute(
            sa.text("UPDATE organization SET follow_up_owner = :display_name WHERE id = :organization_id"),
            {"display_name": display_name, "organization_id": _uuid(5000 + organization_number)},
        )


def downgrade() -> None:
    """移除虚构销售数据和销售专用结构，保留既有单位、成交与同行数据。"""

    opportunity_ids = {f"opportunity{number}": _uuid(10000 + number) for number in range(1, len(OPPORTUNITIES) + 1)}
    placeholders = ", ".join(f":opportunity{number}" for number in range(1, len(OPPORTUNITIES) + 1))
    op.execute(sa.text(f"DELETE FROM opportunity WHERE id IN ({placeholders})").bindparams(**opportunity_ids))
    op.execute(sa.text("""
        UPDATE organization SET follow_up_owner = NULL
        WHERE id IN (:company1, :company2, :company3, :company4, :company5, :company6)
          AND follow_up_owner IN ('张1', '王3', '冯7', '李2', '赵6', '陈4')
    """).bindparams(**{f"company{number}": _uuid(5000 + number) for number in range(1, 7)}))

    op.drop_table("sales_activity")
    op.drop_index("ix_sales_project_salesperson_signed_at", table_name="sales_project")
    op.drop_constraint("fk_sales_project_salesperson_id_salesperson", "sales_project", type_="foreignkey")
    op.drop_column("sales_project", "salesperson_id")
    op.drop_index("ix_opportunity_salesperson_stage", table_name="opportunity")
    op.drop_constraint("fk_opportunity_salesperson_id_salesperson", "opportunity", type_="foreignkey")
    op.drop_column("opportunity", "salesperson_id")
    op.drop_table("salesperson_coverage_city")
    op.drop_table("salesperson")
    sales_activity_type.drop(op.get_bind(), checkfirst=True)
