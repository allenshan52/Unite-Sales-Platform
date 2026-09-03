"""为预计金额和实际成交额补充数据库级非负约束。"""

import sqlalchemy as sa
from alembic import op

revision = "20260819_0016"
down_revision = "20260819_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """先拒绝历史脏数据，再创建与 API 校验一致的金额约束。"""

    connection = op.get_bind()
    negative_opportunities = connection.scalar(
        sa.text("SELECT count(*) FROM opportunity WHERE estimated_amount < 0")
    )
    negative_projects = connection.scalar(
        sa.text("SELECT count(*) FROM sales_project WHERE contract_amount < 0")
    )
    if negative_opportunities or negative_projects:
        raise RuntimeError("检测到负数销售金额，请先修复历史数据后再执行迁移")
    op.create_check_constraint(
        "ck_opportunity_estimated_amount_nonnegative",
        "opportunity",
        "estimated_amount IS NULL OR estimated_amount >= 0",
    )
    op.create_check_constraint(
        "ck_sales_project_contract_amount_nonnegative",
        "sales_project",
        "contract_amount >= 0",
    )


def downgrade() -> None:
    """仅移除本迁移新增的两条金额完整性约束。"""

    op.drop_constraint(
        "ck_sales_project_contract_amount_nonnegative",
        "sales_project",
        type_="check",
    )
    op.drop_constraint(
        "ck_opportunity_estimated_amount_nonnegative",
        "opportunity",
        type_="check",
    )
