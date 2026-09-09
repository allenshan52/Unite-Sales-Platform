"""生产稳定性迁移：增加登录锁定、CSRF、单位乐观锁与软归档字段。"""

import sqlalchemy as sa
from alembic import op

revision = "20260820_0018"
down_revision = "20260819_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """以非空默认值平滑升级现有管理员、会话和单位记录。"""

    op.add_column("admin_user", sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("admin_user", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("admin_user", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    # 旧会话没有配套 CSRF Cookie，升级时主动失效比伪造兼容值更安全。
    op.execute("DELETE FROM admin_session")
    op.add_column("admin_session", sa.Column("csrf_token_hash", sa.String(length=64), nullable=False))
    op.create_index("ix_admin_session_expires_at", "admin_session", ["expires_at"], unique=False)
    op.add_column("organization", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("organization", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.create_index("ix_organization_archived_at", "organization", ["archived_at"], unique=False)


def downgrade() -> None:
    """按依赖逆序移除稳定性字段和索引。"""

    op.drop_index("ix_organization_archived_at", table_name="organization")
    op.drop_column("organization", "version")
    op.drop_column("organization", "archived_at")
    op.drop_index("ix_admin_session_expires_at", table_name="admin_session")
    op.drop_column("admin_session", "csrf_token_hash")
    op.drop_column("admin_user", "last_login_at")
    op.drop_column("admin_user", "locked_until")
    op.drop_column("admin_user", "failed_login_attempts")
