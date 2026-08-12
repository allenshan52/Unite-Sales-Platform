"""为单位主档补充跟进与合作字段，复用既有合作等级枚举。"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260810_0004"
down_revision = "20260810_0003"
branch_labels = None
depends_on = None

cooperation_level = postgresql.ENUM("一级", "二级", "三级", name="cooperation_level", create_type=False)


def upgrade() -> None:
    """新增单位级最近跟进、负责人、合作意向和合作等级字段。"""

    op.add_column("organization", sa.Column("recent_follow_up_at", sa.DateTime(timezone=True)))
    op.add_column("organization", sa.Column("recent_follow_up_content", sa.Text()))
    op.add_column("organization", sa.Column("follow_up_owner", sa.String(120)))
    op.add_column("organization", sa.Column("cooperation_intent", sa.String(500)))
    op.add_column("organization", sa.Column("cooperation_level", cooperation_level))


def downgrade() -> None:
    """仅移除本迁移新增列，保留渠道表仍在使用的合作等级枚举。"""

    for column in (
        "cooperation_level",
        "cooperation_intent",
        "follow_up_owner",
        "recent_follow_up_content",
        "recent_follow_up_at",
    ):
        op.drop_column("organization", column)
