"""为登录账号增加显式销售人员关联，支撑个人 Pin 与全国管理权限分离。"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260827_0032"
down_revision = "20260827_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """新增可空销售人员外键，并为既有本地演示账号补齐确定性关联。"""

    op.add_column("admin_user", sa.Column("salesperson_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_admin_user_salesperson_id",
        "admin_user",
        "salesperson",
        ["salesperson_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_admin_user_salesperson_id", "admin_user", ["salesperson_id"])
    op.execute(sa.text(
        "UPDATE admin_user AS account SET salesperson_id = salesperson.id "
        "FROM (VALUES "
        "('employee1', 'DEMO-S006'), "
        "('hangzhou_sales', 'DEMO-S006'), "
        "('jilin_sales', 'DEMO-S002'), "
        "('jl_ln_sales', 'DEMO-S002'), "
        "('east_manager', 'DEMO-S001')"
        ") AS mapping(username, employee_code) "
        "JOIN salesperson ON salesperson.employee_code = mapping.employee_code "
        "WHERE account.username = mapping.username AND account.salesperson_id IS NULL"
    ))


def downgrade() -> None:
    """移除账号与销售人员关联，保留双方业务主档。"""

    op.drop_index("ix_admin_user_salesperson_id", table_name="admin_user")
    op.drop_constraint("fk_admin_user_salesperson_id", "admin_user", type_="foreignkey")
    op.drop_column("admin_user", "salesperson_id")
