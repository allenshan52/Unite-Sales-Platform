"""同行市场数据库模型测试：验证独立表、金额精度和正式单位关联边界。"""

from app.models import (
    Competitor,
    CompetitorCustomer,
    CompetitorCustomerOrganizationLink,
    CompetitorDeal,
    CompetitorSite,
    CompetitorStrengthRegion,
)
from sqlalchemy import CheckConstraint, Numeric


def test_competitor_tables_are_independent_and_link_explicitly() -> None:
    """同行情报保存在独立表中，仅关联表拥有 organization_id。"""

    assert Competitor.__tablename__ == "competitor"
    for model in (CompetitorSite, CompetitorCustomer, CompetitorDeal, CompetitorStrengthRegion):
        assert "organization_id" not in model.__table__.columns
    assert "organization_id" in CompetitorCustomerOrganizationLink.__table__.columns
    assert CompetitorCustomerOrganizationLink.__table__.columns["competitor_customer_id"].unique is True


def test_competitor_deal_prices_and_quantity_use_fixed_precision() -> None:
    """同行单价、数量和总价使用 NUMERIC，避免竞争金额汇总出现浮点误差。"""

    amount_type = CompetitorDeal.__table__.columns["amount"].type
    unit_price_type = CompetitorDeal.__table__.columns["unit_price"].type
    quantity_type = CompetitorDeal.__table__.columns["quantity"].type
    assert isinstance(amount_type, Numeric)
    assert isinstance(unit_price_type, Numeric)
    assert isinstance(quantity_type, Numeric)
    assert (amount_type.precision, amount_type.scale) == (14, 2)
    assert (unit_price_type.precision, unit_price_type.scale) == (14, 2)
    assert (quantity_type.precision, quantity_type.scale) == (14, 3)
    assert "website_url" in Competitor.__table__.columns
    assert "supplier_name" in CompetitorDeal.__table__.columns


def test_competitor_map_constraints_cover_colors_coordinates_and_regions() -> None:
    """地图颜色、据点坐标、单位坐标和行政区层级均保留数据库约束。"""

    constraint_names = {
        constraint.name
        for model in (Competitor, CompetitorSite, CompetitorCustomer, CompetitorStrengthRegion)
        for constraint in model.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert {
        "ck_competitor_color_hex",
        "ck_competitor_site_gcj02_bounds",
        "ck_competitor_customer_gcj02_bounds",
        "ck_competitor_strength_region_scope",
    } <= constraint_names
