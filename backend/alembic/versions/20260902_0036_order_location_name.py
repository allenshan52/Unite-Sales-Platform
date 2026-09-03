"""为两类成交订单保存高德所在地名称与省市快照。"""

import sqlalchemy as sa
from alembic import op

revision = "20260902_0036"
down_revision = "20260902_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """新增可空所在地字段，保持历史订单原值不变。"""

    op.add_column("sales_project", sa.Column("location_name", sa.String(255), nullable=True))
    op.add_column("competitor_deal", sa.Column("location_name", sa.String(255), nullable=True))
    op.add_column("competitor_deal", sa.Column("province", sa.String(60), nullable=True))
    op.add_column("competitor_deal", sa.Column("city", sa.String(60), nullable=True))


def downgrade() -> None:
    """移除订单所在地快照列，不影响成交单位主档地点。"""

    op.drop_column("competitor_deal", "city")
    op.drop_column("competitor_deal", "province")
    op.drop_column("competitor_deal", "location_name")
    op.drop_column("sales_project", "location_name")
