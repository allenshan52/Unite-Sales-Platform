"""把首期单管理员账号扩展为管理员和普通员工两类站点授权账号。"""

import sqlalchemy as sa
from alembic import op

revision = "20260825_0021"
down_revision = "20260824_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """现有账号全部安全迁移为管理员，再约束后续角色取值。"""

    op.add_column(
        "admin_user",
        sa.Column("role", sa.String(length=20), nullable=False, server_default="管理员"),
    )
    op.create_check_constraint(
        "ck_admin_user_role",
        "admin_user",
        "role IN ('普通员工', '管理员')",
    )
    op.alter_column("admin_user", "role", server_default=None)


def downgrade() -> None:
    """回退角色扩展时移除角色约束与字段，保留全部账号和会话记录。"""

    op.drop_constraint("ck_admin_user_role", "admin_user", type_="check")
    op.drop_column("admin_user", "role")
