"""同行市场公开 API 测试：覆盖首屏懒加载、详情汇总、输入校验和关联状态。"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from app.database import get_db
from app.main import app
from app.models import (
    CompetitorCustomerLevel,
    CompetitorMatchStatus,
    CompetitorSiteType,
    IntelligenceConfidence,
    IntelligenceSourceType,
)
from app.services.competitors import build_public_competitor_detail, calculate_competitor_strength_regions
from fastapi.testclient import TestClient


def _detail_payload() -> dict[str, object]:
    """构造同行详情公开响应，确保测试不依赖真实外部信息。"""

    return {
        "id": str(UUID(int=1)), "name": "同行1", "website_url": "https://example.com", "color": "#147D64", "description": "演示同行",
        "summary": {"site_count": 1, "customer_count": 1, "linked_customer_count": 0, "deal_count": 1, "total_amount": "280000.00", "strong_region_count": 1},
        "sites": [{"id": str(UUID(int=2)), "name": "同行1总部", "site_type": "总部", "address": "演示地址", "province": "上海市", "city": "上海市", "longitude": 121.47, "latitude": 31.23, "source_type": "公开信息", "source_reference": "演示来源", "source_url": None, "confidence": "高", "notes": "演示", "is_primary": True}],
        "customers": [{"id": str(UUID(int=3)), "name": "同行1签约单位1", "customer_level": "一级", "address": "演示地址", "province": "上海市", "city": "上海市", "longitude": 121.48, "latitude": 31.22, "source_type": "公开信息", "source_reference": "演示来源", "source_url": None, "confidence": "高", "first_observed_at": "2025-01-01", "last_verified_at": "2026-01-01", "notes": "演示", "linked_organization_id": None, "linked_organization_name": None, "match_status": None, "match_confidence": None, "deals": [{"id": str(UUID(int=4)), "project_name": "演示项目", "deal_type": "设备采购", "product_name": "台式气相色谱仪", "specification_model": "GC-9860 Plus", "product_image_url": "/cases/jiangsu-lab.webp", "unit_price": "140000.00", "quantity": "2.000", "supplier_name": "虚构供应商", "amount": "280000.00", "signed_at": "2026-01-01", "source_type": "公开信息", "source_reference": "演示来源", "source_url": None, "confidence": "高", "notes": "纯虚构交易金额"}]}],
        "strength_regions": [{"id": str(UUID(int=5)), "region_level": "省", "province": "上海市", "city": None, "strength_level": "强", "source_type": "公开信息", "source_reference": "演示来源", "source_url": None, "confidence": "高", "basis": "演示依据", "score": "1.0000", "site_count": 1, "customer_count": 1, "total_amount": "280000.00"}],
    }


def test_public_competitor_map_items_only_include_pin_data(monkeypatch: pytest.MonkeyPatch, viewer_session: None) -> None:
    """首屏只返回主要据点 Pin，不传输强势区域或内部关联信息。"""

    detail = _detail_payload()
    monkeypatch.setattr("app.routers.competitors.list_public_competitor_map_items", lambda _db, _scope: [{"id": detail["id"], "name": detail["name"], "website_url": detail["website_url"], "color": detail["color"], "description": detail["description"], "primary_site": detail["sites"][0]}])
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/competitors")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert set(response.json()[0]) == {"id", "name", "website_url", "color", "description", "primary_site"}
    assert "customers" not in response.json()[0]


def test_public_competitor_detail_and_invalid_uuid(monkeypatch: pytest.MonkeyPatch, viewer_session: None) -> None:
    """详情返回三类地图实体，非法 UUID 在进入服务前被拒绝。"""

    monkeypatch.setattr("app.routers.competitors.get_public_competitor_detail", lambda _db, _id, _scope: _detail_payload())
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/public/competitors/{UUID(int=1)}")
            invalid = client.get("/api/v1/public/competitors/not-a-uuid")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["customers"][0]["linked_organization_name"] is None
    assert response.json()["customers"][0]["deals"][0]["product_name"] == "台式气相色谱仪"
    assert response.json()["customers"][0]["deals"][0]["unit_price"] == "140000.00"
    assert response.json()["customers"][0]["deals"][0]["quantity"] == "2.000"
    assert response.json()["customers"][0]["deals"][0]["supplier_name"] == "虚构供应商"
    assert response.json()["strength_regions"][0]["strength_level"] == "强"
    assert invalid.status_code == 422


def test_competitor_summary_is_computed_from_records() -> None:
    """同行汇总从据点、单位、交易、关联和区域记录实时计算。"""

    deal = SimpleNamespace(id=UUID(int=4), project_name="演示项目", deal_type="设备采购", product_name="台式气相色谱仪", specification_model="GC-9860 Plus", product_image_url="/cases/jiangsu-lab.webp", unit_price=Decimal("140000.00"), quantity=Decimal("2.000"), supplier_name="虚构供应商", amount=Decimal("280000.00"), signed_at=date(2026, 1, 1), source_type=IntelligenceSourceType.public, source_reference="演示来源", source_url=None, confidence=IntelligenceConfidence.high, notes="纯虚构交易金额")
    organization = SimpleNamespace(id=UUID(int=9), name="公司1")
    link = SimpleNamespace(match_status=CompetitorMatchStatus.confirmed, match_confidence=IntelligenceConfidence.high, organization=organization)
    customer = SimpleNamespace(id=UUID(int=3), name="公司1", customer_level=CompetitorCustomerLevel.level_one, address="演示地址", province="上海市", city="上海市", longitude=121.48, latitude=31.22, source_type=IntelligenceSourceType.public, source_reference="演示来源", source_url=None, confidence=IntelligenceConfidence.high, first_observed_at=date(2025, 1, 1), last_verified_at=date(2026, 1, 1), notes="演示", organization_link=link, deals=[deal])
    site = SimpleNamespace(id=UUID(int=2), name="同行1总部", site_type=CompetitorSiteType.headquarters, address="演示地址", province="上海市", city="上海市", longitude=121.47, latitude=31.23, source_type=IntelligenceSourceType.public, source_reference="演示来源", source_url=None, confidence=IntelligenceConfidence.high, notes="演示", is_primary=True)
    competitor = SimpleNamespace(id=UUID(int=1), name="同行1", website_url="https://example.com", color="#147D64", description="演示同行", sites=[site], customers=[customer])
    detail = build_public_competitor_detail(competitor)
    assert detail.summary.customer_count == 1
    assert detail.summary.linked_customer_count == 1
    assert detail.summary.deal_count == 1
    assert detail.summary.total_amount == Decimal("280000.00")
    assert detail.customers[0].deals[0].specification_model == "GC-9860 Plus"
    assert detail.customers[0].deals[0].quantity == Decimal("2.000")
    assert detail.website_url == "https://example.com"
    assert detail.summary.strong_region_count == 1
    assert detail.strength_regions[0].province == "上海市"


def test_strength_regions_follow_site_customer_and_amount_distribution() -> None:
    """集中、次集中和零散活动分别形成强中弱，完全无活动的省份不会凭空出现。"""

    def customer(number: int, province: str, amount: str) -> SimpleNamespace:
        """构造仅含评分所需字段的虚构成交单位。"""

        return SimpleNamespace(
            province=province,
            longitude=118 + number * 0.1,
            latitude=31 + number * 0.1,
            deals=[SimpleNamespace(amount=Decimal(amount))],
        )

    competitor = SimpleNamespace(
        id=UUID(int=20),
        sites=[
            SimpleNamespace(province="江苏省", site_type=CompetitorSiteType.headquarters, longitude=118.8, latitude=32.0),
            SimpleNamespace(province="浙江省", site_type=CompetitorSiteType.branch, longitude=120.1, latitude=30.2),
            SimpleNamespace(province="安徽省", site_type=CompetitorSiteType.service, longitude=117.2, latitude=31.8),
        ],
        customers=[
            customer(1, "江苏省", "620000"), customer(2, "江苏省", "580000"), customer(3, "江苏省", "540000"),
            customer(4, "浙江省", "420000"), customer(5, "浙江省", "380000"), customer(6, "安徽省", "180000"),
        ],
    )
    regions = calculate_competitor_strength_regions(competitor)
    assert [(region.province, region.strength_level.value) for region in regions] == [
        ("江苏省", "强"), ("浙江省", "中"), ("安徽省", "弱"),
    ]
    assert "福建省" not in {region.province for region in regions}
