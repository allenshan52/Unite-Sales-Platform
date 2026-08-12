"""新增可编辑销售常驻点表，并写入九个明确标记的演示覆盖点。"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260810_0002"
down_revision = "20260805_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建销售常驻点表，并以 GCJ-02 城市中心坐标初始化可编辑的演示网络。"""

    op.create_table(
        "sales_office_location",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("city", sa.String(60), nullable=False),
        sa.Column("address", sa.String(500)),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("coverage_radius_km", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_sales_office_location_city", "sales_office_location", ["city"])
    office_table = sa.table(
        "sales_office_location",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("city", sa.String()),
        sa.column("address", sa.String()),
        sa.column("longitude", sa.Float()),
        sa.column("latitude", sa.Float()),
        sa.column("coverage_radius_km", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
    )
    # 以下记录仅用于演示销售网络；管理员可通过受保护 API 修改地址、坐标、半径和启用状态。
    op.bulk_insert(office_table, [
        {"id": "00000000-0000-4000-8000-000000000101", "name": "杭州销售常驻点（演示）", "city": "杭州市", "address": "杭州市（演示中心点）", "longitude": 120.1551, "latitude": 30.2741, "coverage_radius_km": 420, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000102", "name": "北京销售常驻点（演示）", "city": "北京市", "address": "北京市（演示中心点）", "longitude": 116.4074, "latitude": 39.9042, "coverage_radius_km": 520, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000103", "name": "天津销售常驻点（演示）", "city": "天津市", "address": "天津市（演示中心点）", "longitude": 117.2008, "latitude": 39.0842, "coverage_radius_km": 340, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000104", "name": "沈阳销售常驻点（演示）", "city": "沈阳市", "address": "沈阳市（演示中心点）", "longitude": 123.4315, "latitude": 41.8057, "coverage_radius_km": 480, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000105", "name": "成都销售常驻点（演示）", "city": "成都市", "address": "成都市（演示中心点）", "longitude": 104.0665, "latitude": 30.5723, "coverage_radius_km": 650, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000106", "name": "广州销售常驻点（演示）", "city": "广州市", "address": "广州市（演示中心点）", "longitude": 113.2644, "latitude": 23.1291, "coverage_radius_km": 520, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000107", "name": "武汉销售常驻点（演示）", "city": "武汉市", "address": "武汉市（演示中心点）", "longitude": 114.3054, "latitude": 30.5931, "coverage_radius_km": 580, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000108", "name": "南京销售常驻点（演示）", "city": "南京市", "address": "南京市（演示中心点）", "longitude": 118.7969, "latitude": 32.0603, "coverage_radius_km": 450, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000109", "name": "西安销售常驻点（演示）", "city": "西安市", "address": "西安市（演示中心点）", "longitude": 108.9398, "latitude": 34.3416, "coverage_radius_km": 620, "is_active": True},
    ])


def downgrade() -> None:
    """移除销售常驻点演示数据及其独立业务表。"""

    op.drop_index("ix_sales_office_location_city", table_name="sales_office_location")
    op.drop_table("sales_office_location")
