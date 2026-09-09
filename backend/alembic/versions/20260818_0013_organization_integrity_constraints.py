"""为目标单位名称和唯一主地点补充数据库级并发写入保护。"""

import sqlalchemy as sa
from alembic import op

revision = "20260818_0013"
down_revision = "20260817_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """在已核对无重复数据后创建标准化名称和主地点唯一索引。"""

    op.create_index("uq_organization_normalized_name", "organization", ["normalized_name"], unique=True)
    op.create_index(
        "uq_organization_site_primary",
        "organization_site",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )


def downgrade() -> None:
    """仅移除本迁移新增的完整性索引，不改动单位或地点数据。"""

    op.drop_index("uq_organization_site_primary", table_name="organization_site", postgresql_where=sa.text("is_primary"))
    op.drop_index("uq_organization_normalized_name", table_name="organization")
