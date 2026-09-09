"""补充同行官网，以及同行成交数量和供应商字段。"""

import sqlalchemy as sa
from alembic import op

revision = "20260827_0026"
down_revision = "20260826_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """新增可空情报字段；数量填写时必须为正，总价继续保持独立口径。"""

    op.add_column("competitor", sa.Column("website_url", sa.String(1000)))
    op.add_column("competitor_deal", sa.Column("quantity", sa.Numeric(14, 3)))
    op.add_column("competitor_deal", sa.Column("supplier_name", sa.String(255)))
    op.create_check_constraint(
        "ck_competitor_deal_positive_quantity",
        "competitor_deal",
        "quantity IS NULL OR quantity > 0",
    )


def downgrade() -> None:
    """回退新增字段，不改动既有同行主档和成交情报。"""

    op.drop_constraint("ck_competitor_deal_positive_quantity", "competitor_deal", type_="check")
    op.drop_column("competitor_deal", "supplier_name")
    op.drop_column("competitor_deal", "quantity")
    op.drop_column("competitor", "website_url")
