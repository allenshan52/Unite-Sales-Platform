"""销售覆盖业务口径测试：锁定四级范围、大区映射和组合校验。"""

import pytest
from pydantic import ValidationError

from app.admin_data_schemas import SalespersonProfileInput
from app.sales_coverage import SALES_REGION_PROVINCES, SalesCoverageLevel, normalize_coverage_scope


def test_region_mapping_matches_sales_business_definition() -> None:
    """七个大区必须完整保留用户确认的省份归属。"""

    assert SALES_REGION_PROVINCES == {
        "浙江区": ("浙江", "江西"),
        "东区": ("江苏", "安徽", "上海", "山东", "河南"),
        "北区": ("黑龙江", "辽宁", "吉林", "内蒙古", "河北", "山西", "天津", "北京"),
        "西区": ("云南", "贵州", "湖南", "湖北", "四川", "重庆"),
        "南区": ("广西", "广东", "福建", "海南"),
        "西北": ("陕西", "甘肃", "宁夏", "青海"),
        "其他": ("新疆", "西藏"),
    }


@pytest.mark.parametrize(
    ("level", "name", "province", "city", "adcode"),
    [
        (SalesCoverageLevel.city, "杭州市", "浙江省", "杭州市", "330100"),
        (SalesCoverageLevel.province, "浙江", "浙江省", None, None),
        (SalesCoverageLevel.region, "浙江区", None, None, None),
        (SalesCoverageLevel.national, "全国", None, None, None),
    ],
)
def test_all_coverage_levels_normalize(level, name, province, city, adcode) -> None:
    """四级范围均可规范化，历史省份全称自动兼容。"""

    normalized = normalize_coverage_scope(level, name, province, city, adcode)
    assert normalized.scope_level is level
    assert normalized.scope_name == name


def test_national_scope_cannot_mix_with_other_scopes() -> None:
    """全国覆盖是完整集合，不能再叠加省级或城市级范围。"""

    with pytest.raises(ValidationError, match="全国覆盖不能与其他覆盖范围同时添加"):
        SalespersonProfileInput.model_validate({
            "employee_code": "DEMO-X009",
            "display_name": "演示销售九",
            "color": "#2878B5",
            "coverage_center_longitude": 116.4,
            "coverage_center_latitude": 39.9,
            "is_active": True,
            "coverage_scopes": [
                {"scope_level": "全国", "scope_name": "全国"},
                {"scope_level": "省", "scope_name": "浙江", "province": "浙江"},
            ],
            "activities": [],
        })
