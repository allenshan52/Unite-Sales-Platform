"""把销售覆盖从单一城市升级为市、省、大区、全国四级范围。"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260827_0030"
down_revision = "20260827_0029"
branch_labels = None
depends_on = None

sales_coverage_level = postgresql.ENUM("市", "省", "大区", "全国", name="sales_coverage_level", create_type=False)


def upgrade() -> None:
    """新增覆盖层级和名称，并把全部历史城市记录无损回填为市级范围。"""

    sales_coverage_level.create(op.get_bind(), checkfirst=True)
    op.add_column("salesperson_coverage_city", sa.Column("scope_level", sales_coverage_level))
    op.add_column("salesperson_coverage_city", sa.Column("scope_name", sa.String(60)))
    op.execute(sa.text("UPDATE salesperson_coverage_city SET scope_level = '市', scope_name = city"))
    op.alter_column("salesperson_coverage_city", "scope_level", nullable=False)
    op.alter_column("salesperson_coverage_city", "scope_name", nullable=False)
    op.alter_column("salesperson_coverage_city", "province", existing_type=sa.String(60), nullable=True)
    op.alter_column("salesperson_coverage_city", "city", existing_type=sa.String(60), nullable=True)
    op.alter_column("salesperson_coverage_city", "amap_adcode", existing_type=sa.String(12), nullable=True)
    op.drop_constraint("uq_salesperson_coverage_city", "salesperson_coverage_city", type_="unique")
    op.create_unique_constraint(
        "uq_salesperson_coverage_scope",
        "salesperson_coverage_city",
        ["salesperson_id", "scope_level", "scope_name"],
    )
    op.create_check_constraint(
        "ck_salesperson_coverage_scope_fields",
        "salesperson_coverage_city",
        "(scope_level = '市' AND province IS NOT NULL AND city IS NOT NULL AND amap_adcode IS NOT NULL) OR "
        "(scope_level = '省' AND province IS NOT NULL AND city IS NULL AND amap_adcode IS NULL) OR "
        "(scope_level IN ('大区', '全国') AND province IS NULL AND city IS NULL AND amap_adcode IS NULL)",
    )
    op.create_index(
        "ix_salesperson_coverage_scope_level_name",
        "salesperson_coverage_city",
        ["scope_level", "scope_name"],
    )


def downgrade() -> None:
    """仅在不存在非市级范围时恢复旧城市结构，避免降级静默丢失业务数据。"""

    connection = op.get_bind()
    non_city_count = connection.scalar(sa.text("SELECT count(*) FROM salesperson_coverage_city WHERE scope_level <> '市'"))
    if non_city_count:
        raise RuntimeError("存在省级、大区或全国销售覆盖，无法安全降级为仅城市结构")
    op.drop_index("ix_salesperson_coverage_scope_level_name", table_name="salesperson_coverage_city")
    op.drop_constraint("ck_salesperson_coverage_scope_fields", "salesperson_coverage_city", type_="check")
    op.drop_constraint("uq_salesperson_coverage_scope", "salesperson_coverage_city", type_="unique")
    op.create_unique_constraint(
        "uq_salesperson_coverage_city",
        "salesperson_coverage_city",
        ["salesperson_id", "amap_adcode"],
    )
    op.alter_column("salesperson_coverage_city", "amap_adcode", existing_type=sa.String(12), nullable=False)
    op.alter_column("salesperson_coverage_city", "city", existing_type=sa.String(60), nullable=False)
    op.alter_column("salesperson_coverage_city", "province", existing_type=sa.String(60), nullable=False)
    op.drop_column("salesperson_coverage_city", "scope_name")
    op.drop_column("salesperson_coverage_city", "scope_level")
    sales_coverage_level.drop(op.get_bind(), checkfirst=True)
