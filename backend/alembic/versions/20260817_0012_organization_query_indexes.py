"""为单位分页和一对多关系查询补充兼容性索引。"""

from alembic import op

revision = "20260817_0012"
down_revision = "20260813_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建单位稳定分页及五类高频子记录外键索引。"""

    op.create_index("ix_organization_updated_at_id", "organization", ["updated_at", "id"], unique=False)
    op.create_index("ix_organization_site_organization_id", "organization_site", ["organization_id"], unique=False)
    op.create_index("ix_organization_evidence_organization_id", "organization_evidence", ["organization_id"], unique=False)
    op.create_index("ix_organization_contact_organization_id", "organization_contact", ["organization_id"], unique=False)
    op.create_index("ix_opportunity_organization_id", "opportunity", ["organization_id"], unique=False)
    op.create_index("ix_sales_project_organization_id", "sales_project", ["organization_id"], unique=False)


def downgrade() -> None:
    """按依赖反序移除本迁移新增的查询索引，不改动业务数据。"""

    op.drop_index("ix_sales_project_organization_id", table_name="sales_project")
    op.drop_index("ix_opportunity_organization_id", table_name="opportunity")
    op.drop_index("ix_organization_contact_organization_id", table_name="organization_contact")
    op.drop_index("ix_organization_evidence_organization_id", table_name="organization_evidence")
    op.drop_index("ix_organization_site_organization_id", table_name="organization_site")
    op.drop_index("ix_organization_updated_at_id", table_name="organization")
