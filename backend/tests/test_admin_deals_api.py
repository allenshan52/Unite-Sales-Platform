"""验证统一成交订单后台的认证、组合筛选和多产品响应契约。"""

from types import SimpleNamespace
from uuid import UUID

from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.services.auth import get_current_admin


def _deal_page() -> dict[str, object]:
    """构造不依赖真实客户信息的两产品演示订单分页结果。"""

    return {
        "items": [{
            "id": str(UUID(int=1)), "seller_type": "unite", "seller_id": None, "seller_name": "优纳特",
            "customer_id": str(UUID(int=4)), "opportunity_id": None, "salesperson_id": str(UUID(int=5)),
            "customer_name": "虚构检测单位", "project_name": "演示多产品项目", "total_amount": "300000.00",
            "supplier_name": "虚构供应商", "salesperson_name": "演示销售", "signed_at": "2026-08-01",
            "province": "江苏省", "city": "苏州市", "deal_type": None, "source_reference": None,
            "source_type": None, "source_url": None, "confidence": None, "notes": "纯虚构测试数据",
            "products": [
                {"id": str(UUID(int=2)), "product_name": "演示产品 A", "brand": "虚构品牌甲", "specification_model": "A-1", "product_image_url": None, "unit_price": "100000.00", "quantity": "2.000", "line_total": "200000.00"},
                {"id": str(UUID(int=3)), "product_name": "演示服务 B", "brand": None, "specification_model": None, "product_image_url": None, "unit_price": "100000.00", "quantity": "1.000", "line_total": "100000.00"},
            ],
        }],
        "total": 1, "page": 1, "page_size": 20,
    }


def test_admin_deals_requires_admin_session() -> None:
    """未登录用户不能读取成交订单后台。"""

    with TestClient(app) as client:
        response = client.get("/api/v1/admin-deals")
    assert response.status_code == 401


def test_admin_deals_forwards_filters_and_returns_products(monkeypatch) -> None:
    """管理员组合筛选会完整进入服务层，并返回一笔订单的多条产品。"""

    captured: dict[str, object] = {}

    def fake_list(_db: object, **filters: object) -> dict[str, object]:
        captured.update(filters)
        return _deal_page()

    monkeypatch.setattr("app.routers.admin_deals.list_admin_deals", fake_list)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/admin-deals?seller=competitor&supplier=虚构供应商&competitor_id={UUID(int=9)}&product=产品&year=2026&page=2&page_size=20")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert len(response.json()["items"][0]["products"]) == 2
    assert response.json()["items"][0]["products"][0]["brand"] == "虚构品牌甲"
    assert captured["seller"] == "competitor"
    assert captured["competitor_id"] == UUID(int=9)
    assert captured["year"] == 2026
    assert captured["page"] == 2


def test_admin_deals_rejects_invalid_year_before_service(monkeypatch) -> None:
    """异常年份由路由校验拒绝，不进入数据库查询。"""

    called = False

    def fake_list(_db: object, **_filters: object) -> dict[str, object]:
        nonlocal called
        called = True
        return _deal_page()

    monkeypatch.setattr("app.routers.admin_deals.list_admin_deals", fake_list)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/admin-deals?year=1900")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
    assert called is False


def _unite_order_payload() -> dict[str, object]:
    """构造覆盖订单主字段和两条产品的虚构写入请求。"""

    return {
        "organization_id": str(UUID(int=4)), "opportunity_id": None, "salesperson_id": str(UUID(int=5)),
        "project_name": "演示订单", "total_amount": "300000.00", "supplier_name": "虚构供应商",
        "province": "江苏省", "city": "苏州市", "signed_at": "2026-08-01", "notes": "虚构备注",
        "products": [
            {"product_name": "演示产品 A", "brand": "虚构品牌", "specification_model": "A-1", "unit_price": "100000.00", "quantity": "2", "line_total": "200000.00"},
            {"product_name": "演示服务 B", "brand": None, "specification_model": None, "unit_price": "100000.00", "quantity": "1", "line_total": "100000.00"},
        ],
    }


def test_admin_unite_deal_mutations_require_admin_session() -> None:
    """未登录用户不能从统一页面新增优纳特成交订单。"""

    with TestClient(app) as client:
        response = client.post("/api/v1/admin-deals/unite", json=_unite_order_payload())
    assert response.status_code == 401


def test_admin_unite_deal_create_update_delete_forward_to_services(monkeypatch) -> None:
    """管理员订单级增改删会把完整多产品表单和操作者传给服务层。"""

    calls: list[tuple[str, object]] = []
    deal_id = UUID(int=7)

    def fake_create(_db: object, payload: object, actor: str) -> dict[str, object]:
        calls.append((f"create:{actor}", payload))
        return {"id": deal_id}

    def fake_update(_db: object, received_id: UUID, payload: object, actor: str) -> dict[str, object]:
        calls.append((f"update:{actor}", (received_id, payload)))
        return {"id": received_id}

    def fake_delete(_db: object, received_id: UUID, actor: str) -> None:
        calls.append((f"delete:{actor}", received_id))

    monkeypatch.setattr("app.routers.admin_deals.create_unite_deal", fake_create)
    monkeypatch.setattr("app.routers.admin_deals.update_unite_deal", fake_update)
    monkeypatch.setattr("app.routers.admin_deals.delete_unite_deal", fake_delete)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            created = client.post("/api/v1/admin-deals/unite", json=_unite_order_payload())
            updated = client.put(f"/api/v1/admin-deals/unite/{deal_id}", json=_unite_order_payload())
            deleted = client.delete(f"/api/v1/admin-deals/unite/{deal_id}")
    finally:
        app.dependency_overrides.clear()
    assert created.status_code == 201
    assert updated.status_code == 200
    assert deleted.status_code == 204
    assert [name for name, _value in calls] == ["create:admin_test", "update:admin_test", "delete:admin_test"]
    assert len(calls[0][1].products) == 2


def test_admin_unite_deal_rejects_invalid_amount_before_service(monkeypatch) -> None:
    """负项目总价由请求模式拒绝，不进入写入服务。"""

    called = False

    def fake_create(_db: object, _payload: object, _actor: str) -> dict[str, object]:
        nonlocal called
        called = True
        return {"id": UUID(int=7)}

    payload = _unite_order_payload()
    payload["total_amount"] = "-1"
    monkeypatch.setattr("app.routers.admin_deals.create_unite_deal", fake_create)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/admin-deals/unite", json=payload)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
    assert called is False
