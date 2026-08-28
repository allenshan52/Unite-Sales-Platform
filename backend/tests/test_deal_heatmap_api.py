"""成交金额热力图 API 合同测试：覆盖授权、输入边界和三类读取成功路径。"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from app.database import get_db
from app.main import app
from app.routers import deal_heatmap as router
from app.services import deal_heatmap as deal_heatmap_service
from app.services.account_access import AccountDataScope
from fastapi import HTTPException
from fastapi.testclient import TestClient


def _seller() -> dict[str, str]:
    """构造包含官网的稳定同行卖方响应。"""

    return {"id": str(UUID(int=3)), "name": "同行演示公司", "kind": "competitor", "website_url": "https://example.com"}


def test_deal_heatmap_requires_authorized_session() -> None:
    """未登录用户不能读取公司、金额或订单数据。"""

    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/deal-heatmap/sellers")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401
    assert response.json()["detail"] == "请先登录"


def test_deal_heatmap_success_paths(monkeypatch: pytest.MonkeyPatch, viewer_session: None) -> None:
    """普通员工可读取年份汇总和详情，金额保持 Decimal 字符串。"""

    seller = _seller()
    requested_years: list[int | None] = []

    def summary_response(_db, _seller_id: str, year: int | None, _data_scope):
        """记录汇总年份并返回稳定聚合数据。"""

        requested_years.append(year)
        return {
            "seller": seller,
            "available_years": [2026, 2025, 2024],
            "provinces": [{
                "province": "四川省",
                "signed_amount": Decimal("3150000.00"),
                "signed_order_count": 2,
                "intention_amount": Decimal("1270000.00"),
                "intention_count": 2,
            }],
        }

    def detail_response(_db, _seller_id: str, province: str, year: int | None, _data_scope):
        """记录详情年份，确保点击省份与汇总口径一致。"""

        requested_years.append(year)
        return {
            "seller": seller,
            "province": province,
            "signed_amount": Decimal("3150000.00"),
            "signed_order_count": 1,
            "orders": [{
                "id": UUID(int=1),
                "customer_name": "优纳特演示成交单位12",
                "customer_province": "四川省",
                "customer_city": "成都市",
                "project_name": "演示项目12-A",
                "amount": Decimal("3150000.00"),
                "signed_at": "2026-06-03",
                "notes": "公开招标备注",
            }],
            "intention_amount": Decimal("950000.00"),
            "intention_count": 1,
            "intentions": [{
                "id": UUID(int=2),
                "customer_name": "优纳特演示成交单位12",
                "title": "演示意向12-A",
                "stage": "商务谈判",
                "estimated_amount": Decimal("950000.00"),
                "next_action_at": "2026-09-08",
            }],
        }

    monkeypatch.setattr(router, "list_deal_heatmap_sellers", lambda _db, _scope: [seller])
    monkeypatch.setattr(router, "get_deal_heatmap_summary", summary_response)
    monkeypatch.setattr(router, "get_deal_heatmap_province_detail", detail_response)
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            sellers = client.get("/api/v1/public/deal-heatmap/sellers")
            summary = client.get("/api/v1/public/deal-heatmap/provinces", params={"year": 2026})
            detail = client.get("/api/v1/public/deal-heatmap/provinces/四川省", params={"year": 2026})
    finally:
        app.dependency_overrides.clear()

    assert sellers.status_code == summary.status_code == detail.status_code == 200
    assert summary.json()["available_years"] == [2026, 2025, 2024]
    assert summary.json()["provinces"][0]["signed_amount"] == "3150000.00"
    assert detail.json()["orders"][0]["amount"] == "3150000.00"
    assert detail.json()["seller"]["website_url"] == "https://example.com"
    assert detail.json()["orders"][0]["customer_province"] == "四川省"
    assert detail.json()["orders"][0]["customer_city"] == "成都市"
    assert detail.json()["orders"][0]["notes"] == "公开招标备注"
    assert detail.json()["intentions"][0]["stage"] == "商务谈判"
    assert requested_years == [2026, 2026]


def test_competitor_projection_includes_website_location_and_notes() -> None:
    """服务层一次查询投影同行官网、客户省市和逐笔备注。"""

    competitor_id = UUID(int=3)
    seller_db = MagicMock()
    seller_db.execute.return_value.one_or_none.return_value = SimpleNamespace(
        id=competitor_id,
        name="同行演示公司",
        website_url="https://example.com",
    )
    seller, resolved_id = deal_heatmap_service._resolve_seller(seller_db, str(competitor_id))

    deal = SimpleNamespace(
        id=UUID(int=4),
        project_name="分析设备采购",
        amount=Decimal("680000.00"),
        signed_at=None,
        deal_type="设备采购",
        product_name="分析工作站",
        specification_model="AX-2026",
        product_image_url=None,
        unit_price=Decimal("340000.00"),
        quantity=Decimal("2.000"),
        supplier_name="演示供应商",
        source_type=None,
        source_reference=None,
        source_url=None,
        confidence=None,
        notes="公开招标备注",
    )
    order_db = MagicMock()
    order_db.execute.return_value.all.return_value = [(deal, "华东检测中心", "江苏省", "苏州市")]
    order = deal_heatmap_service._signed_orders(order_db, "江苏省", competitor_id, None)[0]

    assert resolved_id == competitor_id
    assert seller.website_url == "https://example.com"
    assert order.customer_province == "江苏省"
    assert order.customer_city == "苏州市"
    assert order.notes == "公开招标备注"


def test_deal_heatmap_rejects_oversized_seller(viewer_session: None) -> None:
    """异常长公司参数在进入数据库服务前返回 422。"""

    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/deal-heatmap/provinces", params={"seller_id": "x" * 37})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


def test_deal_heatmap_rejects_year_outside_reporting_range(viewer_session: None) -> None:
    """年份超出稳定报表边界时在进入数据库前返回 422。"""

    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/deal-heatmap/provinces", params={"year": 1999})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


def test_unite_heatmap_remains_visible_with_empty_account_scope() -> None:
    """即使账号没有同行地区范围，优纳特卖方仍保持全国可见且不查询同行表。"""

    db = MagicMock()
    seller, competitor_id = deal_heatmap_service._resolve_seller(
        db,
        "unite",
        AccountDataScope(False, frozenset(), frozenset(), frozenset()),
    )

    assert seller.id == "unite"
    assert competitor_id is None
    db.execute.assert_not_called()


def test_competitor_heatmap_rejects_province_outside_account_scope() -> None:
    """同行通过整家公司准入后，省级订单详情仍不能越过账号负责范围。"""

    competitor_id = UUID(int=3)
    db = MagicMock()
    db.execute.return_value.one_or_none.return_value = SimpleNamespace(
        id=competitor_id, name="同行演示公司", website_url=None,
    )
    scope = AccountDataScope(False, frozenset({"吉林", "辽宁"}), frozenset(), frozenset())

    with pytest.raises(HTTPException, match="不能查看该区域") as exc_info:
        deal_heatmap_service.get_deal_heatmap_province_detail(db, str(competitor_id), "四川省", 2026, scope)

    assert exc_info.value.status_code == 403
