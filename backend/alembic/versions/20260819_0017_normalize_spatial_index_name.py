"""移除早期遗留的重复单位地点空间索引。"""

from alembic import op

revision = "20260819_0017"
down_revision = "20260819_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """保留 GeoAlchemy 管理的 idx_ 索引，只删除覆盖相同列的旧 ix_ 索引。"""

    op.execute("DROP INDEX IF EXISTS ix_organization_site_location")


def downgrade() -> None:
    """需要回退时恢复旧索引；当前 idx_ 索引仍会保留。"""

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_organization_site_location "
        "ON organization_site USING gist (location)"
    )
