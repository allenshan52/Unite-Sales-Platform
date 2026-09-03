"""把部分西部数据洞察演示客户迁到沿海城市，使成交热力分布更符合演示目标。"""

import sqlalchemy as sa
from alembic import op


revision = "20260826_0025"
down_revision = "20260825_0024"
branch_labels = None
depends_on = None


REBALANCED_SITES = (
    {
        "organization_id": "00000000-0000-4000-8000-000000023008",
        "source": ("山西省", "大同市", "平城区", "140200", 113.3001, 40.0768, 113.293083448803, 40.075600248378, "大同市平城区演示科创园8号"),
        "target": ("辽宁省", "大连市", "甘井子区", "210200", 121.6147, 38.9140, 121.60975671109382, 38.913222734216795, "大连市甘井子区演示滨海科创园8号"),
    },
    {
        "organization_id": "00000000-0000-4000-8000-000000023010",
        "source": ("内蒙古自治区", "包头市", "九原区", "150200", 109.9681, 40.6006, 109.962369459892, 40.599459140975, "包头市九原区演示科创园10号"),
        "target": ("山东省", "青岛市", "崂山区", "370200", 120.3826, 36.0671, 120.37746691995753, 36.066823772440394, "青岛市崂山区演示滨海科创园10号"),
    },
    {
        "organization_id": "00000000-0000-4000-8000-000000023016",
        "source": ("贵州省", "遵义市", "汇川区", "520300", 106.9336, 27.7493, 106.929761972765, 27.752825900958, "遵义市汇川区演示科创园16号"),
        "target": ("广东省", "深圳市", "南山区", "440300", 114.0579, 22.5431, 114.05278600143454, 22.545817185777537, "深圳市南山区演示滨海科创园16号"),
    },
    {
        "organization_id": "00000000-0000-4000-8000-000000023018",
        "source": ("西藏自治区", "日喀则市", "桑珠孜区", "540200", 88.8851, 29.2675, 88.883068666554, 29.270768421569, "日喀则市桑珠孜区演示科创园18号"),
        "target": ("福建省", "厦门市", "湖里区", "350200", 118.0894, 24.4798, 118.08442291641654, 24.482446768046653, "厦门市湖里区演示滨海科创园18号"),
    },
    {
        "organization_id": "00000000-0000-4000-8000-000000023020",
        "source": ("甘肃省", "天水市", "秦州区", "620500", 105.7249, 34.5809, 105.720963089870, 34.582217961355, "天水市秦州区演示科创园20号"),
        "target": ("江苏省", "苏州市", "姑苏区", "320500", 120.5853, 31.2989, 120.58112257724488, 31.301084697397616, "苏州市姑苏区演示滨海科创园20号"),
    },
    {
        "organization_id": "00000000-0000-4000-8000-000000023022",
        "source": ("青海省", "海东市", "平安区", "630200", 102.1043, 36.5029, 102.102230099533, 36.502835386291, "海东市平安区演示科创园22号"),
        "target": ("浙江省", "宁波市", "鄞州区", "330200", 121.5503, 29.8746, 121.546142379319, 29.877183302310847, "宁波市鄞州区演示滨海科创园22号"),
    },
    {
        "organization_id": "00000000-0000-4000-8000-000000023024",
        "source": ("宁夏回族自治区", "吴忠市", "利通区", "640300", 106.1984, 37.9976, 106.194000973107, 37.997056633479, "吴忠市利通区演示科创园24号"),
        "target": ("河北省", "秦皇岛市", "海港区", "130300", 119.6005, 39.9354, 119.59472929503868, 39.934291825980914, "秦皇岛市海港区演示滨海科创园24号"),
    },
    {
        "organization_id": "00000000-0000-4000-8000-000000023026",
        "source": ("新疆维吾尔自治区", "昌吉回族自治州", "昌吉市", "652300", 87.3082, 44.0112, 87.305088875877, 44.009883189990, "昌吉回族自治州昌吉市演示科创园26号"),
        "target": ("广西壮族自治区", "北海市", "海城区", "450500", 109.1193, 21.4733, 109.11500715915017, 21.475685236790543, "北海市海城区演示滨海科创园26号"),
    },
)


def _validate_rebalance() -> None:
    """锁定迁移规模和东西部范围，避免后续误扩到非演示单位。"""

    assert len(REBALANCED_SITES) == 8
    assert len({row["organization_id"] for row in REBALANCED_SITES}) == 8
    assert {row["source"][0] for row in REBALANCED_SITES} == {
        "山西省", "内蒙古自治区", "贵州省", "西藏自治区", "甘肃省", "青海省", "宁夏回族自治区", "新疆维吾尔自治区",
    }
    assert {row["target"][1] for row in REBALANCED_SITES} == {
        "大连市", "青岛市", "深圳市", "厦门市", "苏州市", "宁波市", "秦皇岛市", "北海市",
    }


def _apply_locations(destination_key: str, expected_key: str) -> None:
    """仅对带数据洞察演示标记且仍处于预期省份的主地点执行原子迁移。"""

    connection = op.get_bind()
    statement = sa.text("""
        UPDATE organization_site AS site
        SET raw_address = :address,
            address = :address,
            province = :province,
            city = :city,
            district = :district,
            amap_adcode = :amap_adcode,
            longitude = :longitude,
            latitude = :latitude,
            location = ST_SetSRID(ST_MakePoint(:wgs_longitude, :wgs_latitude), 4326)
        WHERE site.organization_id = CAST(:organization_id AS uuid)
          AND site.is_primary IS TRUE
          AND site.province = :expected_province
          AND EXISTS (
              SELECT 1 FROM organization AS organization
              WHERE organization.id = site.organization_id
                AND organization.attributes->>'data_insights_demo' = 'true'
          )
    """)
    for row in REBALANCED_SITES:
        province, city, district, adcode, longitude, latitude, wgs_longitude, wgs_latitude, address = row[destination_key]
        result = connection.execute(statement, {
            "organization_id": row["organization_id"],
            "expected_province": row[expected_key][0],
            "province": province,
            "city": city,
            "district": district,
            "amap_adcode": adcode,
            "longitude": longitude,
            "latitude": latitude,
            "wgs_longitude": wgs_longitude,
            "wgs_latitude": wgs_latitude,
            "address": address,
        })
        if result.rowcount != 1:
            raise RuntimeError(f"演示热力地点迁移失败：{row['organization_id']}")


def upgrade() -> None:
    """把八家西部演示客户迁到八个沿海城市，保留订单金额和时间口径。"""

    _validate_rebalance()
    _apply_locations("target", "source")


def downgrade() -> None:
    """将八家演示客户完整恢复到原西部城市及原坐标。"""

    _validate_rebalance()
    _apply_locations("source", "target")
