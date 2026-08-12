"""新增渠道合作方覆盖网络，并写入十八条分散省会城市的演示数据。"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260810_0003"
down_revision = "20260810_0002"
branch_labels = None
depends_on = None

partner_type = sa.Enum("经销商", "代理商", "合作伙伴", name="channel_partner_type")
cooperation_level = sa.Enum("一级", "二级", "三级", name="cooperation_level")


def upgrade() -> None:
    """创建可编辑渠道档案表，并初始化三类各六个演示覆盖点。"""

    op.create_table(
        "channel_partner_location",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("partner_type", partner_type, nullable=False),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("longitude", sa.Float()),
        sa.Column("latitude", sa.Float()),
        sa.Column("display_longitude", sa.Float(), nullable=False),
        sa.Column("display_latitude", sa.Float(), nullable=False),
        sa.Column("authorized_coverage_area", sa.String(500)),
        sa.Column("coverage_radius_km", sa.Integer(), nullable=False),
        sa.Column("authorized_product_lines", postgresql.JSONB()),
        sa.Column("cooperation_level", cooperation_level, nullable=False),
        sa.Column("contract_info", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_channel_partner_location_partner_type", "channel_partner_location", ["partner_type"])
    op.create_index("ix_channel_partner_location_cooperation_level", "channel_partner_location", ["cooperation_level"])
    channel_table = sa.table(
        "channel_partner_location",
        sa.column("id", postgresql.UUID(as_uuid=True)), sa.column("name", sa.String()),
        sa.column("partner_type", partner_type), sa.column("address", sa.String()),
        sa.column("longitude", sa.Float()), sa.column("latitude", sa.Float()),
        sa.column("display_longitude", sa.Float()), sa.column("display_latitude", sa.Float()),
        sa.column("authorized_coverage_area", sa.String()), sa.column("coverage_radius_km", sa.Integer()),
        sa.column("authorized_product_lines", postgresql.JSONB()), sa.column("cooperation_level", cooperation_level),
        sa.column("contract_info", sa.Text()), sa.column("notes", sa.Text()), sa.column("is_active", sa.Boolean()),
    )
    # 真实经纬度及业务授权字段按需求留空；display_* 仅承载当前省会中心演示位置。
    op.bulk_insert(channel_table, [
        {"id": "00000000-0000-4000-8000-000000000201", "name": "经销商1", "partner_type": "经销商", "address": "济南市市中心（演示）", "longitude": None, "latitude": None, "display_longitude": 117.1201, "display_latitude": 36.6512, "authorized_coverage_area": None, "coverage_radius_km": 380, "authorized_product_lines": None, "cooperation_level": "一级", "contract_info": None, "notes": None, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000202", "name": "经销商2", "partner_type": "经销商", "address": "长沙市市中心（演示）", "longitude": None, "latitude": None, "display_longitude": 112.9388, "display_latitude": 28.2282, "authorized_coverage_area": None, "coverage_radius_km": 420, "authorized_product_lines": None, "cooperation_level": "二级", "contract_info": None, "notes": None, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000203", "name": "经销商3", "partner_type": "经销商", "address": "昆明市市中心（演示）", "longitude": None, "latitude": None, "display_longitude": 102.8329, "display_latitude": 24.8801, "authorized_coverage_area": None, "coverage_radius_km": 520, "authorized_product_lines": None, "cooperation_level": "三级", "contract_info": None, "notes": None, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000204", "name": "经销商4", "partner_type": "经销商", "address": "哈尔滨市市中心（演示）", "longitude": None, "latitude": None, "display_longitude": 126.6424, "display_latitude": 45.7567, "authorized_coverage_area": None, "coverage_radius_km": 480, "authorized_product_lines": None, "cooperation_level": "一级", "contract_info": None, "notes": None, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000205", "name": "经销商5", "partner_type": "经销商", "address": "福州市市中心（演示）", "longitude": None, "latitude": None, "display_longitude": 119.2965, "display_latitude": 26.0745, "authorized_coverage_area": None, "coverage_radius_km": 300, "authorized_product_lines": None, "cooperation_level": "二级", "contract_info": None, "notes": None, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000206", "name": "经销商6", "partner_type": "经销商", "address": "乌鲁木齐市市中心（演示）", "longitude": None, "latitude": None, "display_longitude": 87.6168, "display_latitude": 43.8256, "authorized_coverage_area": None, "coverage_radius_km": 720, "authorized_product_lines": None, "cooperation_level": "三级", "contract_info": None, "notes": None, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000207", "name": "代理商1", "partner_type": "代理商", "address": "石家庄市市中心（演示）", "longitude": None, "latitude": None, "display_longitude": 114.5149, "display_latitude": 38.0428, "authorized_coverage_area": None, "coverage_radius_km": 360, "authorized_product_lines": None, "cooperation_level": "二级", "contract_info": None, "notes": None, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000208", "name": "代理商2", "partner_type": "代理商", "address": "南昌市市中心（演示）", "longitude": None, "latitude": None, "display_longitude": 115.8582, "display_latitude": 28.6829, "authorized_coverage_area": None, "coverage_radius_km": 400, "authorized_product_lines": None, "cooperation_level": "三级", "contract_info": None, "notes": None, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000209", "name": "代理商3", "partner_type": "代理商", "address": "南宁市市中心（演示）", "longitude": None, "latitude": None, "display_longitude": 108.3669, "display_latitude": 22.8170, "authorized_coverage_area": None, "coverage_radius_km": 460, "authorized_product_lines": None, "cooperation_level": "一级", "contract_info": None, "notes": None, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000210", "name": "代理商4", "partner_type": "代理商", "address": "兰州市市中心（演示）", "longitude": None, "latitude": None, "display_longitude": 103.8343, "display_latitude": 36.0611, "authorized_coverage_area": None, "coverage_radius_km": 520, "authorized_product_lines": None, "cooperation_level": "二级", "contract_info": None, "notes": None, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000211", "name": "代理商5", "partner_type": "代理商", "address": "长春市市中心（演示）", "longitude": None, "latitude": None, "display_longitude": 125.3235, "display_latitude": 43.8171, "authorized_coverage_area": None, "coverage_radius_km": 430, "authorized_product_lines": None, "cooperation_level": "三级", "contract_info": None, "notes": None, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000212", "name": "代理商6", "partner_type": "代理商", "address": "贵阳市市中心（演示）", "longitude": None, "latitude": None, "display_longitude": 106.6302, "display_latitude": 26.6470, "authorized_coverage_area": None, "coverage_radius_km": 340, "authorized_product_lines": None, "cooperation_level": "一级", "contract_info": None, "notes": None, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000213", "name": "合作伙伴1", "partner_type": "合作伙伴", "address": "合肥市市中心（演示）", "longitude": None, "latitude": None, "display_longitude": 117.2272, "display_latitude": 31.8206, "authorized_coverage_area": None, "coverage_radius_km": 390, "authorized_product_lines": None, "cooperation_level": "三级", "contract_info": None, "notes": None, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000214", "name": "合作伙伴2", "partner_type": "合作伙伴", "address": "太原市市中心（演示）", "longitude": None, "latitude": None, "display_longitude": 112.5489, "display_latitude": 37.8706, "authorized_coverage_area": None, "coverage_radius_km": 350, "authorized_product_lines": None, "cooperation_level": "一级", "contract_info": None, "notes": None, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000215", "name": "合作伙伴3", "partner_type": "合作伙伴", "address": "呼和浩特市市中心（演示）", "longitude": None, "latitude": None, "display_longitude": 111.7492, "display_latitude": 40.8426, "authorized_coverage_area": None, "coverage_radius_km": 600, "authorized_product_lines": None, "cooperation_level": "二级", "contract_info": None, "notes": None, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000216", "name": "合作伙伴4", "partner_type": "合作伙伴", "address": "海口市市中心（演示）", "longitude": None, "latitude": None, "display_longitude": 110.1983, "display_latitude": 20.0440, "authorized_coverage_area": None, "coverage_radius_km": 280, "authorized_product_lines": None, "cooperation_level": "三级", "contract_info": None, "notes": None, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000217", "name": "合作伙伴5", "partner_type": "合作伙伴", "address": "重庆市市中心（演示）", "longitude": None, "latitude": None, "display_longitude": 106.5516, "display_latitude": 29.5630, "authorized_coverage_area": None, "coverage_radius_km": 550, "authorized_product_lines": None, "cooperation_level": "一级", "contract_info": None, "notes": None, "is_active": True},
        {"id": "00000000-0000-4000-8000-000000000218", "name": "合作伙伴6", "partner_type": "合作伙伴", "address": "西宁市市中心（演示）", "longitude": None, "latitude": None, "display_longitude": 101.7782, "display_latitude": 36.6171, "authorized_coverage_area": None, "coverage_radius_km": 650, "authorized_product_lines": None, "cooperation_level": "二级", "contract_info": None, "notes": None, "is_active": True},
    ])


def downgrade() -> None:
    """移除渠道合作方演示数据、表和专用枚举。"""

    op.drop_index("ix_channel_partner_location_cooperation_level", table_name="channel_partner_location")
    op.drop_index("ix_channel_partner_location_partner_type", table_name="channel_partner_location")
    op.drop_table("channel_partner_location")
    cooperation_level.drop(op.get_bind(), checkfirst=True)
    partner_type.drop(op.get_bind(), checkfirst=True)
