"""创建独立客户集团树，并写入明确标记的虚构演示数据。"""

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260812_0005"
down_revision = "20260810_0004"
branch_labels = None
depends_on = None

opportunity_stage = postgresql.ENUM(
    "已识别",
    "资格确认",
    "方案/报价",
    "商务谈判",
    "已关闭失单",
    name="opportunity_stage",
    create_type=False,
)


def upgrade() -> None:
    """创建集团主档与自关联单位树，并初始化三组纯虚构地图数据。"""

    op.create_table(
        "customer_group",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("color ~ '^#[0-9A-Fa-f]{6}$'", name="ck_customer_group_color_hex"),
    )
    op.create_table(
        "customer_group_unit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customer_group.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customer_group_unit.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_headquarters", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("province", sa.String(60), nullable=False),
        sa.Column("city", sa.String(60), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("location", Geometry("POINT", srid=4326, spatial_index=False)),
        sa.Column("is_won", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("actual_sales_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("opportunity_stage", opportunity_stage),
        sa.Column("estimated_opportunity_amount", sa.Numeric(14, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("group_id", "name", name="uq_customer_group_unit_name"),
        sa.CheckConstraint(
            "(is_headquarters AND parent_id IS NULL) OR (NOT is_headquarters AND parent_id IS NOT NULL)",
            name="ck_customer_group_unit_tree_role",
        ),
        sa.CheckConstraint(
            "(is_won AND actual_sales_amount > 0) OR (NOT is_won AND actual_sales_amount = 0)",
            name="ck_customer_group_unit_deal_amount",
        ),
        sa.CheckConstraint("estimated_opportunity_amount IS NULL OR estimated_opportunity_amount >= 0", name="ck_customer_group_unit_estimated_amount"),
        sa.CheckConstraint("longitude BETWEEN 72.004 AND 137.8347 AND latitude BETWEEN 0.8293 AND 55.8271", name="ck_customer_group_unit_gcj02_bounds"),
    )
    op.create_index("ix_customer_group_unit_group_id", "customer_group_unit", ["group_id"])
    op.create_index("ix_customer_group_unit_province_city", "customer_group_unit", ["province", "city"])
    op.create_index("idx_customer_group_unit_location", "customer_group_unit", ["location"], postgresql_using="gist")
    op.create_index(
        "uq_customer_group_single_headquarters",
        "customer_group_unit",
        ["group_id"],
        unique=True,
        postgresql_where=sa.text("is_headquarters"),
    )
    op.execute(
        """
        CREATE FUNCTION prevent_customer_group_unit_cycle()
        RETURNS trigger AS $$
        DECLARE
            parent_group_id uuid;
        BEGIN
            IF NEW.parent_id IS NULL THEN
                RETURN NEW;
            END IF;

            IF NEW.parent_id = NEW.id THEN
                RAISE EXCEPTION '集团单位不能将自身设为父级' USING ERRCODE = '23514';
            END IF;

            SELECT group_id INTO parent_group_id
            FROM customer_group_unit
            WHERE id = NEW.parent_id;

            IF parent_group_id IS NOT NULL AND parent_group_id <> NEW.group_id THEN
                RAISE EXCEPTION '集团单位父级必须属于同一集团' USING ERRCODE = '23514';
            END IF;

            IF EXISTS (
                WITH RECURSIVE ancestors AS (
                    SELECT id, parent_id
                    FROM customer_group_unit
                    WHERE id = NEW.parent_id
                    UNION ALL
                    SELECT unit.id, unit.parent_id
                    FROM customer_group_unit AS unit
                    JOIN ancestors ON unit.id = ancestors.parent_id
                )
                SELECT 1 FROM ancestors WHERE id = NEW.id
            ) THEN
                RAISE EXCEPTION '集团单位层级不能形成循环' USING ERRCODE = '23514';
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_customer_group_unit_no_cycle
        BEFORE INSERT OR UPDATE OF parent_id, group_id ON customer_group_unit
        FOR EACH ROW EXECUTE FUNCTION prevent_customer_group_unit_cycle();
        """
    )

    group_table = sa.table(
        "customer_group",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("color", sa.String()),
    )
    # 以下名称、地址、坐标和金额全部为产品演示数据，不对应真实客户或交易。
    op.bulk_insert(
        group_table,
        [
            {"id": "00000000-0000-4000-8000-000000000301", "name": "集团1", "color": "#1F8A70"},
            {"id": "00000000-0000-4000-8000-000000000302", "name": "集团2", "color": "#F59E0B"},
            {"id": "00000000-0000-4000-8000-000000000303", "name": "集团3", "color": "#3B7A57"},
        ],
    )
    unit_table = sa.table(
        "customer_group_unit",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("group_id", postgresql.UUID(as_uuid=True)),
        sa.column("parent_id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("is_headquarters", sa.Boolean()),
        sa.column("address", sa.String()),
        sa.column("province", sa.String()),
        sa.column("city", sa.String()),
        sa.column("longitude", sa.Float()),
        sa.column("latitude", sa.Float()),
        sa.column("is_won", sa.Boolean()),
        sa.column("actual_sales_amount", sa.Numeric(14, 2)),
        sa.column("opportunity_stage", opportunity_stage),
        sa.column("estimated_opportunity_amount", sa.Numeric(14, 2)),
    )
    units = [
        (401, 301, None, "集团1", True, "杭州市市中心（演示地址）", "浙江省", "杭州市", 120.1551, 30.2741, True, 1200000, "商务谈判", 300000, 120.1504055, 30.2764288),
        (402, 301, 401, "集团1一级分支1", False, "上海市市中心（演示地址）", "上海市", "上海市", 121.4737, 31.2304, True, 680000, None, None, 121.4691769, 31.2323423),
        (403, 301, 401, "集团1一级分支2", False, "南京市市中心（演示地址）", "江苏省", "南京市", 118.7969, 32.0603, False, 0, "方案/报价", 900000, 118.7917164, 32.0623757),
        (404, 301, 402, "集团1二级分支1", False, "苏州市市中心（演示地址）", "江苏省", "苏州市", 120.5853, 31.2989, False, 0, "资格确认", 350000, 120.5811226, 31.3010847),
        (405, 302, None, "集团2", True, "北京市市中心（演示地址）", "北京市", "北京市", 116.4074, 39.9042, False, 0, "已识别", 500000, 116.4011577, 39.9027967),
        (406, 302, 405, "集团2一级分支1", False, "天津市市中心（演示地址）", "天津市", "天津市", 117.2008, 39.0842, True, 860000, None, None, 117.1945020, 39.0831939),
        (407, 302, 405, "集团2一级分支2", False, "石家庄市市中心（演示地址）", "河北省", "石家庄市", 114.5149, 38.0428, False, 0, None, None, 114.5089265, 38.0421811),
        (408, 302, 406, "集团2二级分支1", False, "济南市市中心（演示地址）", "山东省", "济南市", 117.1201, 36.6512, True, 420000, "商务谈判", 200000, 117.1139722, 36.6507702),
        (409, 303, None, "集团3", True, "广州市市中心（演示地址）", "广东省", "广州市", 113.2644, 23.1291, True, 1500000, None, None, 113.2590704, 23.1317767),
        (410, 303, 409, "集团3一级分支1", False, "深圳市市中心（演示地址）", "广东省", "深圳市", 114.0579, 22.5431, False, 0, "方案/报价", 780000, 114.0527860, 22.5458172),
        (411, 303, 409, "集团3一级分支2", False, "武汉市市中心（演示地址）", "湖北省", "武汉市", 114.3054, 30.5931, True, 560000, None, None, 114.2999552, 30.5955095),
        (412, 303, 411, "集团3二级分支1", False, "成都市市中心（演示地址）", "四川省", "成都市", 104.0665, 30.5723, False, 0, "已关闭失单", 0, 104.0639951, 30.5747545),
    ]
    op.bulk_insert(
        unit_table,
        [
            {
                "id": f"00000000-0000-4000-8000-000000000{unit_id}",
                "group_id": f"00000000-0000-4000-8000-000000000{group_id}",
                "parent_id": f"00000000-0000-4000-8000-000000000{parent_id}" if parent_id else None,
                "name": name,
                "is_headquarters": is_headquarters,
                "address": address,
                "province": province,
                "city": city,
                "longitude": longitude,
                "latitude": latitude,
                "is_won": is_won,
                "actual_sales_amount": actual_sales_amount,
                "opportunity_stage": stage,
                "estimated_opportunity_amount": estimated_amount,
            }
            for unit_id, group_id, parent_id, name, is_headquarters, address, province, city, longitude, latitude, is_won, actual_sales_amount, stage, estimated_amount, _wgs_longitude, _wgs_latitude in units
        ],
    )
    for unit_id, *_fields, wgs_longitude, wgs_latitude in units:
        op.execute(
            sa.text(
                "UPDATE customer_group_unit "
                "SET location = ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326) "
                "WHERE id = CAST(:id AS uuid)"
            ).bindparams(
                id=f"00000000-0000-4000-8000-000000000{unit_id}",
                longitude=wgs_longitude,
                latitude=wgs_latitude,
            )
        )
    op.alter_column("customer_group_unit", "location", existing_type=Geometry("POINT", srid=4326), nullable=False)


def downgrade() -> None:
    """移除集团演示树、约束触发器及两张独立业务表。"""

    op.execute("DROP TRIGGER IF EXISTS trg_customer_group_unit_no_cycle ON customer_group_unit")
    op.execute("DROP FUNCTION IF EXISTS prevent_customer_group_unit_cycle()")
    op.drop_table("customer_group_unit")
    op.drop_table("customer_group")
