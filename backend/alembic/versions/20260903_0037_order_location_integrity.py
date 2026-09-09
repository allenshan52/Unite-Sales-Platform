"""强化两类成交订单所在地快照的数据完整性，并补齐常用关联与日期索引。"""

from alembic import op

revision = "20260903_0037"
down_revision = "20260902_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """约束新写入的省市必须成对出现；历史脏数据暂不阻断迁移。"""

    op.execute(
        "ALTER TABLE sales_project ADD CONSTRAINT ck_sales_project_location_pair "
        "CHECK ((province IS NULL AND city IS NULL) OR (province IS NOT NULL AND city IS NOT NULL)) NOT VALID"
    )
    op.execute(
        "ALTER TABLE competitor_deal ADD CONSTRAINT ck_competitor_deal_location_pair "
        "CHECK ((province IS NULL AND city IS NULL) OR (province IS NOT NULL AND city IS NOT NULL)) NOT VALID"
    )
    op.create_index("ix_sales_project_opportunity_id", "sales_project", ["opportunity_id"])
    op.create_index("ix_competitor_deal_signed_at", "competitor_deal", ["signed_at"])


def downgrade() -> None:
    """移除本次索引与所在地成对约束，保留订单数据本身。"""

    op.drop_index("ix_competitor_deal_signed_at", table_name="competitor_deal")
    op.drop_index("ix_sales_project_opportunity_id", table_name="sales_project")
    op.drop_constraint("ck_competitor_deal_location_pair", "competitor_deal", type_="check")
    op.drop_constraint("ck_sales_project_location_pair", "sales_project", type_="check")
