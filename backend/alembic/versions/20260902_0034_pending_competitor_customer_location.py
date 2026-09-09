"""允许成交订单自动建立待补地址的同行成交单位。"""

import sqlalchemy as sa
from alembic import op

revision = "20260902_0034"
down_revision = "20260828_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """放宽地址和成对坐标，并保留中国范围坐标约束。"""

    op.drop_constraint("ck_competitor_customer_gcj02_bounds", "competitor_customer", type_="check")
    op.alter_column("competitor_customer", "address", existing_type=sa.String(500), nullable=True)
    op.alter_column("competitor_customer", "longitude", existing_type=sa.Float(), nullable=True)
    op.alter_column("competitor_customer", "latitude", existing_type=sa.Float(), nullable=True)
    op.create_check_constraint(
        "ck_competitor_customer_gcj02_bounds",
        "competitor_customer",
        "(longitude IS NULL AND latitude IS NULL) OR "
        "(longitude IS NOT NULL AND latitude IS NOT NULL AND "
        "longitude BETWEEN 72.004 AND 137.8347 AND latitude BETWEEN 0.8293 AND 55.8271)",
    )


def downgrade() -> None:
    """仅在不存在待补地址记录时恢复原非空约束。"""

    op.drop_constraint("ck_competitor_customer_gcj02_bounds", "competitor_customer", type_="check")
    op.alter_column("competitor_customer", "latitude", existing_type=sa.Float(), nullable=False)
    op.alter_column("competitor_customer", "longitude", existing_type=sa.Float(), nullable=False)
    op.alter_column("competitor_customer", "address", existing_type=sa.String(500), nullable=False)
    op.create_check_constraint(
        "ck_competitor_customer_gcj02_bounds",
        "competitor_customer",
        "longitude BETWEEN 72.004 AND 137.8347 AND latitude BETWEEN 0.8293 AND 55.8271",
    )
