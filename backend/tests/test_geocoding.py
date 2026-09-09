"""高德坐标处理单元测试：不访问网络，也不读取任何真实 Key。"""

from app.services import geocoding
from app.services.geocoding import GeocodeMatch, _is_name_only_address, _is_verified_poi_name, _normalized_name, gcj02_to_wgs84, search_amap_places
from app.services.organizations import _postgis_location


def test_exact_level_allows_map_pin() -> None:
    """兴趣点和高德门址级结果可安全代表高校地址，因此允许进入地图。"""

    assert GeocodeMatch(116.3, 39.9, "110108", "兴趣点").is_exact is True
    assert GeocodeMatch(117.3, 39.1, "120112", "门址").is_exact is True


def test_low_precision_level_does_not_allow_map_pin() -> None:
    """区县级地址不能代表单位门址，必须保留待人工核验。"""

    assert GeocodeMatch(116.3, 39.9, "110000", "区县").is_exact is False


def test_gcj_coordinate_is_converted_for_postgis() -> None:
    """中国境内的 GCJ-02 点应转换后再写入 WGS84 PostGIS 字段。"""

    longitude, latitude = gcj02_to_wgs84(116.397128, 39.916527)
    assert longitude < 116.397128
    assert latitude < 39.916527


def test_admin_coordinate_uses_same_postgis_conversion() -> None:
    """管理员手工新增/修改地点与自动地理编码必须写入同一 WGS84 空间口径。"""

    location = _postgis_location(116.397128, 39.916527)
    expected_longitude, expected_latitude = gcj02_to_wgs84(116.397128, 39.916527)

    assert location is not None
    assert location.data == f"POINT({expected_longitude} {expected_latitude})"


def test_name_normalization_preserves_chinese_name_for_exact_match() -> None:
    """名称比较只忽略展示空白，不会放宽成包含关系匹配。"""

    assert _normalized_name(" 清华 大学 ") == _normalized_name("清华大学")


def test_campus_name_is_allowed_but_independent_college_is_rejected() -> None:
    """同校校区可用，而名称相近的独立学院不是同一目标单位。"""

    assert _is_verified_poi_name("西安交通大学", "西安交通大学兴庆校区") is True
    assert _is_verified_poi_name("西安交通大学", "西安交通大学城市学院") is False


def test_name_only_address_can_use_an_exact_main_poi_but_not_an_unrelated_address() -> None:
    """历史粗地址仅在“城市加学校名”时允许由严格同名 POI 补齐，避免放宽任意地址匹配。"""

    assert _is_name_only_address("成都市四川大学", "四川大学") is True
    assert _is_name_only_address("成都市武侯区一环路南一段24号", "四川大学") is False


def test_company_location_search_normalizes_amap_poi(monkeypatch) -> None:
    """公司地点搜索把高德 POI 规范为前端可直接回填的地址和六位坐标。"""

    monkeypatch.setattr(geocoding, "_request_amap_json", lambda _endpoint, _query, **_options: {
        "pois": [{
            "name": "高德演示公司", "address": "演示大道18号", "pname": "上海市",
            "cityname": [], "adname": "浦东新区", "adcode": "310115", "location": "121.506377,31.245105",
        }],
    })

    results = search_amap_places("高德演示公司")

    assert results == [{
        "name": "高德演示公司", "address": "上海市浦东新区演示大道18号",
        "province": "上海市", "city": "上海市", "district": "浦东新区",
        "amap_adcode": "310115", "longitude": "121.506377", "latitude": "31.245105",
    }]
