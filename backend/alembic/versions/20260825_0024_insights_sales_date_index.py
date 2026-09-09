"""为数据洞察年度和季度聚合增加成交日期索引。"""

from alembic import op


revision = "20260825_0024"
down_revision = "20260825_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """按签约日期加速全年、季度和月度实际销售范围查询。"""

    op.create_index("ix_sales_project_signed_at", "sales_project", ["signed_at"])


def downgrade() -> None:
    """回滚数据洞察专用成交日期索引。"""

    op.drop_index("ix_sales_project_signed_at", table_name="sales_project")
