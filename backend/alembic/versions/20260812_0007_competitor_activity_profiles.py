"""重排虚构同行据点与成交数据，使区域强度可由真实加权算法复算。"""

from collections.abc import Mapping, Sequence

from alembic import op
import sqlalchemy as sa


revision = "20260812_0007"
down_revision = "20260812_0006"
branch_labels = None
depends_on = None


def _uuid(number: int) -> str:
    """生成与上一版演示数据一致的稳定 UUID。"""

    return f"00000000-0000-4000-8000-{number:012d}"


LOCATIONS = {
    "上海": ("上海市", "上海市", 121.4737, 31.2304),
    "北京": ("北京市", "北京市", 116.4074, 39.9042),
    "广州": ("广东省", "广州市", 113.2644, 23.1291),
    "成都": ("四川省", "成都市", 104.0665, 30.5723),
    "武汉": ("湖北省", "武汉市", 114.3054, 30.5931),
    "南京": ("江苏省", "南京市", 118.7969, 32.0603),
    "西安": ("陕西省", "西安市", 108.9398, 34.3416),
    "沈阳": ("辽宁省", "沈阳市", 123.4315, 41.8057),
    "济南": ("山东省", "济南市", 117.1201, 36.6512),
    "杭州": ("浙江省", "杭州市", 120.1551, 30.2741),
    "厦门": ("福建省", "厦门市", 118.0894, 24.4798),
    "郑州": ("河南省", "郑州市", 113.6254, 34.7466),
    "长沙": ("湖南省", "长沙市", 112.9388, 28.2282),
    "重庆": ("重庆市", "重庆市", 106.5516, 29.5630),
    "合肥": ("安徽省", "合肥市", 117.2272, 31.8206),
    "石家庄": ("河北省", "石家庄市", 114.5149, 38.0428),
    "长春": ("吉林省", "长春市", 125.3235, 43.8171),
    "南宁": ("广西壮族自治区", "南宁市", 108.3669, 22.8170),
}

SITE_PROFILES = {
    1: (("上海", "总部"), ("上海", "服务点")),
    2: (("北京", "总部"), ("石家庄", "分部")),
    3: (("广州", "总部"),),
    4: (("成都", "总部"), ("重庆", "服务点")),
    5: (("武汉", "总部"),),
    6: (("南京", "总部"), ("杭州", "分部"), ("合肥", "服务点")),
    7: (("西安", "总部"),),
    8: (("沈阳", "总部"), ("长春", "服务点")),
    9: (("济南", "总部"),),
    10: (("厦门", "总部"), ("广州", "分部")),
}

CUSTOMER_PROFILES = {
    1: ("上海", "上海", "上海", "上海", "上海", "杭州"),
    2: ("北京", "北京", "北京", "北京", "石家庄", "石家庄"),
    3: ("广州", "广州", "广州", "广州", "广州", "广州"),
    4: ("成都", "成都", "成都", "成都", "重庆", "重庆"),
    5: ("武汉", "武汉", "武汉", "武汉", "武汉", "长沙"),
    6: ("南京", "南京", "南京", "杭州", "杭州", "合肥"),
    7: ("西安", "西安", "西安", "西安", "西安", "西安"),
    8: ("沈阳", "沈阳", "沈阳", "沈阳", "长春", "长春"),
    9: ("济南", "济南", "济南", "济南", "石家庄", "北京"),
    10: ("厦门", "厦门", "厦门", "广州", "广州", "上海"),
}

DEAL_AMOUNTS = {
    1: (820000, 760000, 690000, 620000, 540000, 180000),
    2: (680000, 640000, 590000, 520000, 250000, 210000),
    3: (900000, 820000, 760000, 700000, 650000, 600000),
    4: (780000, 720000, 660000, 590000, 280000, 240000),
    5: (740000, 690000, 630000, 580000, 520000, 190000),
    6: (620000, 580000, 540000, 420000, 380000, 180000),
    7: (700000, 660000, 620000, 580000, 540000, 500000),
    8: (650000, 610000, 560000, 500000, 230000, 190000),
    9: (620000, 570000, 520000, 470000, 180000, 160000),
    10: (650000, 600000, 550000, 430000, 390000, 180000),
}


def _apply_activity_profiles(
    site_profiles: Mapping[int, Sequence[tuple[str, str]]],
    customer_profiles: Mapping[int, Sequence[str]],
    deal_amounts: Mapping[int, Sequence[int]],
) -> None:
    """按稳定 ID 更新演示据点、成交单位和金额，并同步三个正式单位的主地址。"""

    connection = op.get_bind()
    for competitor_number in range(1, 11):
        competitor_id = _uuid(600 + competitor_number)
        site_ids = [row.id for row in connection.execute(sa.text(
            "SELECT id FROM competitor_site WHERE competitor_id = :competitor_id ORDER BY is_primary DESC, id"
        ), {"competitor_id": competitor_id})]
        for index, (site_id, (location_key, site_type)) in enumerate(zip(site_ids, site_profiles[competitor_number], strict=True)):
            province, city, longitude, latitude = LOCATIONS[location_key]
            offset = _coordinate_offset(index)
            connection.execute(sa.text("""
                UPDATE competitor_site
                SET name = :name, site_type = :site_type, address = :address, province = :province,
                    city = :city, longitude = :longitude, latitude = :latitude,
                    source_reference = :source_reference, notes = :notes
                WHERE id = :site_id
            """), {
                "site_id": site_id,
                "name": f"同行{competitor_number}{city}{site_type}",
                "site_type": site_type,
                "address": f"{city}演示{site_type}地址",
                "province": province,
                "city": city,
                "longitude": longitude + offset,
                "latitude": latitude + offset,
                "source_reference": "演示数据：集中型同行据点样例",
                "notes": "纯虚构同行据点，用于验证区域评分",
            })

        customer_ids = [row.id for row in connection.execute(sa.text(
            "SELECT id FROM competitor_customer WHERE competitor_id = :competitor_id ORDER BY id"
        ), {"competitor_id": competitor_id})]
        for index, (customer_id, location_key, amount) in enumerate(
            zip(customer_ids, customer_profiles[competitor_number], deal_amounts[competitor_number], strict=True),
            start=1,
        ):
            province, city, longitude, latitude = LOCATIONS[location_key]
            connection.execute(sa.text("""
                UPDATE competitor_customer
                SET address = :address, province = :province, city = :city,
                    longitude = :longitude, latitude = :latitude,
                    source_reference = :source_reference, notes = :notes
                WHERE id = :customer_id
            """), {
                "customer_id": customer_id,
                "address": f"{city}演示成交单位地址{index}",
                "province": province,
                "city": city,
                "longitude": longitude + index * 0.018,
                "latitude": latitude - index * 0.013,
                "source_reference": "演示数据：区域集中型同行成交样例",
                "notes": "纯虚构同行成交单位，用于验证数量与金额评分",
            })
            connection.execute(sa.text(
                "UPDATE competitor_deal SET amount = :amount WHERE competitor_customer_id = :customer_id"
            ), {"customer_id": customer_id, "amount": amount})

    for organization_index, competitor_number in enumerate((1, 2, 3), start=1):
        location_key = customer_profiles[competitor_number][0]
        province, city, longitude, latitude = LOCATIONS[location_key]
        connection.execute(sa.text("""
            UPDATE organization_site
            SET raw_address = :address, address = :address, province = :province, city = :city,
                longitude = :longitude, latitude = :latitude
            WHERE id = :site_id
        """), {
            "site_id": _uuid(5100 + organization_index),
            "address": f"{city}演示地址",
            "province": province,
            "city": city,
            "longitude": longitude + 0.018,
            "latitude": latitude - 0.013,
        })


def _coordinate_offset(index: int) -> float:
    """让同城多个据点轻微错开，避免 Pin 完全重叠。"""

    return index * 0.035


def upgrade() -> None:
    """应用集中型同行画像，并清除已被实时算法取代的随机区域演示行。"""

    _apply_activity_profiles(SITE_PROFILES, CUSTOMER_PROFILES, DEAL_AMOUNTS)
    op.execute("DELETE FROM competitor_strength_region")


def downgrade() -> None:
    """恢复 0006 的均匀散布演示数据和静态三级区域记录。"""

    city_keys = tuple(LOCATIONS)
    old_extra_sites = {1: (("厦门", "服务点"),), 2: (("石家庄", "分部"),), 4: (("长沙", "服务点"),), 6: (("杭州", "分部"), ("合肥", "服务点")), 8: (("长春", "服务点"),), 10: (("广州", "分部"),)}
    old_sites = {number: ((city_keys[number - 1], "总部"), *old_extra_sites.get(number, ())) for number in range(1, 11)}
    old_customers = {
        number: tuple(city_keys[((number - 1) * 3 + unit - 1) % len(city_keys)] for unit in range(1, 7))
        for number in range(1, 11)
    }
    old_amounts = {
        number: tuple(180000 + number * 37000 + unit * 29000 for unit in range(1, 7))
        for number in range(1, 11)
    }
    _apply_activity_profiles(old_sites, old_customers, old_amounts)

    region_table = sa.table(
        "competitor_strength_region",
        *[sa.column(name) for name in ("id", "competitor_id", "region_level", "province", "city", "strength_level", "source_type", "source_reference", "source_url", "confidence", "basis")],
    )
    sources = (("强", "公开信息", "高"), ("中", "一线反馈", "中"), ("弱", "推测", "低"))
    rows = []
    sequence = 4000
    for number in range(1, 11):
        for level_index, city_index in enumerate((number - 1, (number + 4) % len(city_keys), (number + 9) % len(city_keys))):
            sequence += 1
            province, city, _longitude, _latitude = LOCATIONS[city_keys[city_index]]
            strength, source_type, confidence = sources[level_index]
            rows.append({
                "id": _uuid(sequence),
                "competitor_id": _uuid(600 + number),
                "region_level": "省" if level_index == 0 else "市",
                "province": province,
                "city": None if level_index == 0 else city,
                "strength_level": strength,
                "source_type": source_type,
                "source_reference": f"演示数据：{source_type}区域判断样例",
                "source_url": None,
                "confidence": confidence,
                "basis": f"根据同行{number}虚构成交分布与据点覆盖，标记为{strength}势区域。",
            })
    op.bulk_insert(region_table, rows)
