"""将优纳特与同行成交订单规范化为订单主表和多条产品明细。"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260827_0028"
down_revision = "20260827_0027"
branch_labels = None
depends_on = None


def _create_product_table(table_name: str, parent_table: str, parent_column: str, *, include_image: bool) -> None:
    """创建带顺序、金额约束和级联删除的订单产品明细表。"""

    columns: list[sa.Column | sa.Constraint] = [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(parent_column, postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{parent_table}.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("specification_model", sa.String(255)),
    ]
    if include_image:
        columns.append(sa.Column("product_image_url", sa.String(1000)))
    columns.extend(
        [
            sa.Column("unit_price", sa.Numeric(14, 2)),
            sa.Column("quantity", sa.Numeric(14, 3)),
            sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint("unit_price IS NULL OR unit_price > 0", name=f"ck_{table_name}_unit_price_positive"),
            sa.CheckConstraint("quantity IS NULL OR quantity > 0", name=f"ck_{table_name}_quantity_positive"),
            sa.CheckConstraint("line_total >= 0", name=f"ck_{table_name}_line_total_nonnegative"),
            sa.UniqueConstraint(parent_column, "position", name=f"uq_{table_name}_position", deferrable=True, initially="DEFERRED"),
        ]
    )
    op.create_table(table_name, *columns)
    op.create_index(f"ix_{table_name}_{parent_column}", table_name, [parent_column])


def upgrade() -> None:
    """新增两张明细表，并把每笔旧订单转换为第一条产品，保证历史数据不丢失。"""

    _create_product_table("sales_project_product", "sales_project", "sales_project_id", include_image=False)
    _create_product_table("competitor_deal_product", "competitor_deal", "competitor_deal_id", include_image=True)

    op.execute(
        """
        INSERT INTO sales_project_product
            (sales_project_id, product_name, specification_model, unit_price, quantity, line_total, position)
        SELECT id, name, specification_model, unit_price, quantity, contract_amount, 0
        FROM sales_project
        """
    )
    op.execute(
        """
        INSERT INTO competitor_deal_product
            (competitor_deal_id, product_name, specification_model, product_image_url,
             unit_price, quantity, line_total, position)
        SELECT id, COALESCE(NULLIF(product_name, ''), project_name), specification_model,
               product_image_url, unit_price, quantity, amount, 0
        FROM competitor_deal
        """
    )


def downgrade() -> None:
    """移除多产品明细；兼容列仍保留，但降级会丢失新增的第二条及后续产品。"""

    op.drop_index("ix_competitor_deal_product_competitor_deal_id", table_name="competitor_deal_product")
    op.drop_table("competitor_deal_product")
    op.drop_index("ix_sales_project_product_sales_project_id", table_name="sales_project_product")
    op.drop_table("sales_project_product")
