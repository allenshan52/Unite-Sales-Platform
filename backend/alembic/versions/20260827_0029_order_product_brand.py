"""为优纳特与同行订单的每条产品明细增加独立品牌字段。"""

import sqlalchemy as sa
from alembic import op

revision = "20260827_0029"
down_revision = "20260827_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """新增可空品牌列，保留无法可靠推断品牌的历史产品数据。"""

    op.add_column("sales_project_product", sa.Column("brand", sa.String(255)))
    op.add_column("competitor_deal_product", sa.Column("brand", sa.String(255)))


def downgrade() -> None:
    """移除两张产品明细表的品牌列。"""

    op.drop_column("competitor_deal_product", "brand")
    op.drop_column("sales_project_product", "brand")
