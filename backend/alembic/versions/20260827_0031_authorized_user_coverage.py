"""建立普通用户/超级管理员身份及账号四级数据覆盖范围。"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260827_0031"
down_revision = "20260827_0030"
branch_labels = None
depends_on = None

sales_coverage_level = postgresql.ENUM("市", "省", "大区", "全国", name="sales_coverage_level", create_type=False)


def upgrade() -> None:
    """把 admin_syt 固定为超级管理员，其他账号转为普通用户并创建范围表。"""

    op.drop_constraint("ck_admin_user_role", "admin_user", type_="check")
    op.execute(sa.text(
        "UPDATE admin_user SET role = CASE WHEN username = 'admin_syt' THEN '超级管理员' ELSE '普通用户' END"
    ))
    op.create_check_constraint(
        "ck_admin_user_role",
        "admin_user",
        "role IN ('普通用户', '超级管理员')",
    )
    op.create_table(
        "admin_user_coverage_scope",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_level", sales_coverage_level, nullable=False),
        sa.Column("scope_name", sa.String(length=60), nullable=False),
        sa.Column("province", sa.String(length=60)),
        sa.Column("city", sa.String(length=60)),
        sa.Column("amap_adcode", sa.String(length=12)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amap_adcode ~ '^[0-9]{6}$'", name="ck_admin_user_coverage_scope_adcode"),
        sa.CheckConstraint(
            "(scope_level = '市' AND province IS NOT NULL AND city IS NOT NULL AND amap_adcode IS NOT NULL) OR "
            "(scope_level = '省' AND province IS NOT NULL AND city IS NULL AND amap_adcode IS NULL) OR "
            "(scope_level IN ('大区', '全国') AND province IS NULL AND city IS NULL AND amap_adcode IS NULL)",
            name="ck_admin_user_coverage_scope_fields",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["admin_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "scope_level", "scope_name", name="uq_admin_user_coverage_scope"),
    )
    op.create_index("ix_admin_user_coverage_scope_user", "admin_user_coverage_scope", ["user_id"])
    op.create_index(
        "ix_admin_user_coverage_scope_level_name",
        "admin_user_coverage_scope",
        ["scope_level", "scope_name"],
    )
    op.execute(sa.text(
        "INSERT INTO admin_user_coverage_scope "
        "(id, user_id, scope_level, scope_name, province, city, amap_adcode) "
        "SELECT gen_random_uuid(), id, '全国', '全国', NULL, NULL, NULL "
        "FROM admin_user WHERE username = 'admin_syt'"
    ))


def downgrade() -> None:
    """移除账号范围，并把新身份名称恢复为旧两级角色。"""

    op.drop_index("ix_admin_user_coverage_scope_level_name", table_name="admin_user_coverage_scope")
    op.drop_index("ix_admin_user_coverage_scope_user", table_name="admin_user_coverage_scope")
    op.drop_table("admin_user_coverage_scope")
    op.drop_constraint("ck_admin_user_role", "admin_user", type_="check")
    op.execute(sa.text(
        "UPDATE admin_user SET role = CASE WHEN role = '超级管理员' THEN '管理员' ELSE '普通员工' END"
    ))
    op.create_check_constraint(
        "ck_admin_user_role",
        "admin_user",
        "role IN ('普通员工', '管理员')",
    )
