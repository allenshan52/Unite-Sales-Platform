"""补充优纳特成交项目的产品、供应商和成交所在地字段。"""

import sqlalchemy as sa
from alembic import op

revision = "20260827_0027"
down_revision = "20260827_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """以可空列兼容历史订单，并约束填写后的单价和数量必须为正数。"""

    op.add_column("sales_project", sa.Column("unit_price", sa.Numeric(14, 2)))
    op.add_column("sales_project", sa.Column("quantity", sa.Numeric(14, 3)))
    op.add_column("sales_project", sa.Column("supplier_name", sa.String(255)))
    op.add_column("sales_project", sa.Column("specification_model", sa.String(255)))
    op.add_column("sales_project", sa.Column("province", sa.String(60)))
    op.add_column("sales_project", sa.Column("city", sa.String(60)))
    op.create_check_constraint("ck_sales_project_unit_price_positive", "sales_project", "unit_price IS NULL OR unit_price > 0")
    op.create_check_constraint("ck_sales_project_quantity_positive", "sales_project", "quantity IS NULL OR quantity > 0")


def downgrade() -> None:
    """回退新增明细字段，不改动既有成交项目核心字段。"""

    op.drop_constraint("ck_sales_project_quantity_positive", "sales_project", type_="check")
    op.drop_constraint("ck_sales_project_unit_price_positive", "sales_project", type_="check")
    op.drop_column("sales_project", "city")
    op.drop_column("sales_project", "province")
    op.drop_column("sales_project", "specification_model")
    op.drop_column("sales_project", "supplier_name")
    op.drop_column("sales_project", "quantity")
    op.drop_column("sales_project", "unit_price")
