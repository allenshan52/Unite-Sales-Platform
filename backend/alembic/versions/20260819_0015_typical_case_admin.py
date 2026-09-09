"""收紧一省一案约束，让草稿和关联项目也保持全局唯一。"""

import sqlalchemy as sa
from alembic import op

revision = "20260819_0015"
down_revision = "20260818_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """确认历史数据无重复后，将仅发布唯一升级为所有状态唯一。"""

    op.execute("""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM typical_case GROUP BY province HAVING count(*) > 1) THEN
            RAISE EXCEPTION '典型案例存在重复省份，请先合并后再升级';
          END IF;
          IF EXISTS (SELECT 1 FROM typical_case WHERE sales_project_id IS NOT NULL GROUP BY sales_project_id HAVING count(*) > 1) THEN
            RAISE EXCEPTION '典型案例存在重复成交项目，请先解除重复关联后再升级';
          END IF;
        END $$;
    """)
    op.drop_index("uq_typical_case_published_province", table_name="typical_case", postgresql_where=sa.text("is_published"))
    op.drop_index("uq_typical_case_published_project", table_name="typical_case", postgresql_where=sa.text("is_published AND sales_project_id IS NOT NULL"))
    op.create_index("uq_typical_case_province", "typical_case", ["province"], unique=True)
    op.create_index("uq_typical_case_project", "typical_case", ["sales_project_id"], unique=True, postgresql_where=sa.text("sales_project_id IS NOT NULL"))


def downgrade() -> None:
    """恢复只约束已发布案例的旧规则，不删除任何案例数据。"""

    op.drop_index("uq_typical_case_project", table_name="typical_case", postgresql_where=sa.text("sales_project_id IS NOT NULL"))
    op.drop_index("uq_typical_case_province", table_name="typical_case")
    op.create_index("uq_typical_case_published_province", "typical_case", ["province"], unique=True, postgresql_where=sa.text("is_published"))
    op.create_index("uq_typical_case_published_project", "typical_case", ["sales_project_id"], unique=True, postgresql_where=sa.text("is_published AND sales_project_id IS NOT NULL"))
