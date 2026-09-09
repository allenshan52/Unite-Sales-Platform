"""允许同行订单暂缺成交类型与来源情报。"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260902_0035"
down_revision = "20260902_0034"
branch_labels = None
depends_on = None

source_type_enum = postgresql.ENUM("公开信息", "一线反馈", "推测", name="intelligence_source_type", create_type=False)
confidence_enum = postgresql.ENUM("高", "中", "低", name="intelligence_confidence", create_type=False)


def upgrade() -> None:
    """移除四个订单情报字段的非空约束，不改写已有数据。"""

    op.alter_column("competitor_deal", "deal_type", existing_type=sa.String(80), nullable=True)
    op.alter_column("competitor_deal", "source_type", existing_type=source_type_enum, nullable=True)
    op.alter_column("competitor_deal", "source_reference", existing_type=sa.String(500), nullable=True)
    op.alter_column("competitor_deal", "confidence", existing_type=confidence_enum, nullable=True)


def downgrade() -> None:
    """用明确的待补标记回填空值后恢复旧版非空约束。"""

    op.execute(
        sa.text(
            "UPDATE competitor_deal SET "
            "deal_type = COALESCE(deal_type, '未填写'), "
            "source_type = COALESCE(source_type, '推测'::intelligence_source_type), "
            "source_reference = COALESCE(source_reference, '待补充'), "
            "confidence = COALESCE(confidence, '低'::intelligence_confidence) "
            "WHERE deal_type IS NULL OR source_type IS NULL OR source_reference IS NULL OR confidence IS NULL"
        )
    )
    op.alter_column("competitor_deal", "confidence", existing_type=confidence_enum, nullable=False)
    op.alter_column("competitor_deal", "source_reference", existing_type=sa.String(500), nullable=False)
    op.alter_column("competitor_deal", "source_type", existing_type=source_type_enum, nullable=False)
    op.alter_column("competitor_deal", "deal_type", existing_type=sa.String(80), nullable=False)
