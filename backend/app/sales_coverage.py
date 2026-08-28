"""销售覆盖业务口径：集中定义市、省、大区、全国四级范围及大区省份映射。"""

import enum
from dataclasses import dataclass


class SalesCoverageLevel(str, enum.Enum):
    """销售人员可选择的四级覆盖范围。"""

    city = "市"
    province = "省"
    region = "大区"
    national = "全国"


SALES_REGION_PROVINCES: dict[str, tuple[str, ...]] = {
    "浙江区": ("浙江", "江西"),
    "东区": ("江苏", "安徽", "上海", "山东", "河南"),
    "北区": ("黑龙江", "辽宁", "吉林", "内蒙古", "河北", "山西", "天津", "北京"),
    "西区": ("云南", "贵州", "湖南", "湖北", "四川", "重庆"),
    "南区": ("广西", "广东", "福建", "海南"),
    "西北": ("陕西", "甘肃", "宁夏", "青海"),
    "其他": ("新疆", "西藏"),
}
SALES_PROVINCES: tuple[str, ...] = tuple(dict.fromkeys(
    province
    for provinces in SALES_REGION_PROVINCES.values()
    for province in provinces
))

_PROVINCE_ALIASES = {province: province for province in SALES_PROVINCES}
_PROVINCE_ALIASES.update({
    "北京市": "北京", "天津市": "天津", "上海市": "上海", "重庆市": "重庆",
    "内蒙古自治区": "内蒙古", "广西壮族自治区": "广西", "西藏自治区": "西藏",
    "宁夏回族自治区": "宁夏", "新疆维吾尔自治区": "新疆",
})
for _province in SALES_PROVINCES:
    _PROVINCE_ALIASES.setdefault(f"{_province}省", _province)


@dataclass(frozen=True)
class NormalizedCoverageScope:
    """返回可直接持久化的规范化覆盖范围字段。"""

    scope_level: SalesCoverageLevel
    scope_name: str
    province: str | None
    city: str | None
    amap_adcode: str | None


def canonical_province(value: str | None) -> str | None:
    """把省级行政区全称归一为业务使用的短名称。"""

    if value is None:
        return None
    return _PROVINCE_ALIASES.get(value.strip())


def normalize_coverage_scope(
    scope_level: SalesCoverageLevel,
    scope_name: str,
    province: str | None,
    city: str | None,
    amap_adcode: str | None,
) -> NormalizedCoverageScope:
    """按层级校验并清理覆盖字段，阻止互相矛盾的省、市和大区组合。"""

    name = scope_name.strip()
    province_value = province.strip() if province else None
    city_value = city.strip() if city else None
    adcode_value = amap_adcode.strip() if amap_adcode else None

    if scope_level is SalesCoverageLevel.national:
        if name != "全国" or province_value or city_value or adcode_value:
            raise ValueError("全国覆盖只能填写范围名称“全国”")
        return NormalizedCoverageScope(scope_level, "全国", None, None, None)

    if scope_level is SalesCoverageLevel.region:
        if name not in SALES_REGION_PROVINCES or province_value or city_value or adcode_value:
            raise ValueError("大区覆盖必须选择系统预设的大区")
        return NormalizedCoverageScope(scope_level, name, None, None, None)

    normalized_province = canonical_province(province_value or name)
    if normalized_province is None:
        raise ValueError("省份必须来自系统预设的省级行政区")

    if scope_level is SalesCoverageLevel.province:
        if canonical_province(name) != normalized_province or city_value or adcode_value:
            raise ValueError("省级覆盖只能填写一个省份")
        return NormalizedCoverageScope(scope_level, normalized_province, normalized_province, None, None)

    if not city_value or name != city_value or not adcode_value or not adcode_value.isdigit() or len(adcode_value) != 6:
        raise ValueError("市级覆盖必须填写省份、城市和六位高德行政区编码")
    return NormalizedCoverageScope(scope_level, city_value, normalized_province, city_value, adcode_value)


def included_provinces(scope_level: SalesCoverageLevel, scope_name: str, province: str | None) -> list[str]:
    """把大区和全国范围展开为省份列表，供公开地图和后续统计复用。"""

    if scope_level is SalesCoverageLevel.national:
        return list(SALES_PROVINCES)
    if scope_level is SalesCoverageLevel.region:
        return list(SALES_REGION_PROVINCES.get(scope_name, ()))
    normalized = canonical_province(province or scope_name)
    return [normalized] if normalized else []
