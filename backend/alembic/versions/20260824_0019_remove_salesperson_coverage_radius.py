"""销售地图改为只显示 Pin，移除不再使用的人员覆盖半径字段。"""

import sqlalchemy as sa
from alembic import op

revision = "20260824_0019"
down_revision = "20260820_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """删除销售人员覆盖半径及其约束，并兼容已提前移除字段的本地数据库。"""

    inspector = sa.inspect(op.get_bind())
    constraints = {item["name"] for item in inspector.get_check_constraints("salesperson")}
    if "ck_salesperson_coverage_radius_km" in constraints:
        op.drop_constraint("ck_salesperson_coverage_radius_km", "salesperson", type_="check")
    columns = {item["name"] for item in inspector.get_columns("salesperson")}
    if "coverage_radius_km" in columns:
        op.drop_column("salesperson", "coverage_radius_km")


def downgrade() -> None:
    """回退时以 300 公里默认值补回非空半径字段和范围约束。"""

    inspector = sa.inspect(op.get_bind())
    columns = {item["name"] for item in inspector.get_columns("salesperson")}
    if "coverage_radius_km" not in columns:
        op.add_column(
            "salesperson",
            sa.Column("coverage_radius_km", sa.Integer(), nullable=False, server_default="300"),
        )
        op.alter_column("salesperson", "coverage_radius_km", server_default=None)
    constraints = {item["name"] for item in sa.inspect(op.get_bind()).get_check_constraints("salesperson")}
    if "ck_salesperson_coverage_radius_km" not in constraints:
        op.create_check_constraint(
            "ck_salesperson_coverage_radius_km",
            "salesperson",
            "coverage_radius_km BETWEEN 1 AND 2000",
        )
