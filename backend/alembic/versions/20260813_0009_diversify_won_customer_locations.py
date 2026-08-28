"""调整六家优纳特已成交演示公司的城市分布，并同步 PostGIS 展示坐标。"""

import sqlalchemy as sa
from alembic import op


revision = "20260813_0009"
down_revision = "20260813_0008"
branch_labels = None
depends_on = None


def _uuid(number: int) -> str:
    """生成与既有演示单位迁移一致的稳定 UUID。"""

    return f"00000000-0000-4000-8000-{number:012d}"


NEW_LOCATIONS = (
    (1, "江苏省", "盐城市", "亭湖区", "盐城市亭湖区演示产业园1号", 120.1636, 33.3474, 120.15865711040836, 33.3488387891318),
    (2, "吉林省", "吉林市", "昌邑区", "吉林市昌邑区演示产业园2号", 126.5494, 43.8378, 126.54370965523908, 43.83554601181915),
    (3, "广东省", "湛江市", "赤坎区", "湛江市赤坎区演示产业园3号", 110.3594, 21.2707, 110.35490356846306, 21.273081980572794),
    (4, "重庆市", "重庆市", "渝北区", "重庆市渝北区演示产业园4号", 106.5516, 29.5630, 106.54788235020013, 29.565848726332526),
    (5, "浙江省", "金华市", "婺城区", "金华市婺城区演示产业园5号", 119.6474, 29.0791, 119.64269506545439, 29.082076171592423),
    (6, "广西壮族自治区", "柳州市", "城中区", "柳州市城中区演示产业园6号", 109.4281, 24.3264, 109.42349998037008, 24.32910051197779),
)

OLD_LOCATIONS = (
    (1, "上海市", "上海市", "浦东新区", "上海市演示地址", 121.4917, 31.2174, 121.4872399874631, 31.219400058174497),
    (2, "北京市", "北京市", "海淀区", "北京市演示地址", 116.4254, 39.8912, 116.4191748922385, 39.889808378924684),
    (3, "广东省", "广州市", "天河区", "广州市演示地址", 113.2824, 23.1161, 113.2770533530674, 23.11876643007988),
    (4, "天津市", "天津市", "滨海新区", "天津市滨海新区演示产业园4号", 117.2009, 39.0842, 117.19460215656956, 39.08319405250946),
    (5, "浙江省", "杭州市", "滨江区", "杭州市滨江区演示产业园5号", 120.1551, 30.2741, 120.15040552070364, 30.276428776799747),
    (6, "广东省", "深圳市", "南山区", "深圳市南山区演示产业园6号", 114.0579, 22.5431, 114.05278600143454, 22.545817185777537),
)


def _apply_locations(locations: tuple[tuple[object, ...], ...]) -> None:
    """原子更新业务地址、GCJ-02 展示坐标和 WGS84 PostGIS 点位。"""

    connection = op.get_bind()
    for number, province, city, district, address, longitude, latitude, wgs_longitude, wgs_latitude in locations:
        connection.execute(
            sa.text("""
                UPDATE organization_site
                SET raw_address = :address, address = :address,
                    province = :province, city = :city, district = :district,
                    longitude = :longitude, latitude = :latitude,
                    location = ST_SetSRID(ST_MakePoint(:wgs_longitude, :wgs_latitude), 4326)
                WHERE id = :site_id
            """),
            {
                "site_id": _uuid(5100 + int(number)),
                "address": address,
                "province": province,
                "city": city,
                "district": district,
                "longitude": longitude,
                "latitude": latitude,
                "wgs_longitude": wgs_longitude,
                "wgs_latitude": wgs_latitude,
            },
        )


def upgrade() -> None:
    """把六家虚构客户分散到东北、华东、华南和西南城市。"""

    _apply_locations(NEW_LOCATIONS)


def downgrade() -> None:
    """恢复上一迁移中的六个省会及一线城市演示位置。"""

    _apply_locations(OLD_LOCATIONS)
