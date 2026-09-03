"""为账号会话撤销增加用户外键索引，避免停用账号时扫描完整会话表。"""

from alembic import op

revision = "20260828_0033"
down_revision = "20260827_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """索引会话用户外键，保持现有会话和账号数据不变。"""

    op.create_index("ix_admin_session_user_id", "admin_session", ["user_id"])


def downgrade() -> None:
    """仅移除用户索引，不删除任何会话记录。"""

    op.drop_index("ix_admin_session_user_id", table_name="admin_session")
