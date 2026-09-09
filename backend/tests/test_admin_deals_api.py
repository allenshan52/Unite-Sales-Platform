"""验证成交订单后台的认证、筛选、两类写入和跨归属转换契约。"""

from types import SimpleNamespace
from uuid import UUID

from sqlalchemy.dialects import postgresql

from app.database import get_db
from app.main import app
from app.services.auth import get_current_admin
from app.services.admin_deals import list_admin_deals
from fastapi.testclient import TestClient


def _deal_page() -> dict[str, object]:
    """构造不依赖真实客户信息的两产品演示订单分页结果。"""

    return {
        "items": [{
            "id": str(UUID(int=1)), "seller_type": "unite", "seller_id": None, "seller_name": "优纳特",
            "customer_id": str(UUID(int=4)), "opportunity_id": None, "salesperson_id": str(UUID(int=5)),
            "customer_name": "虚构检测单位", "project_name": "演示多产品项目", "total_amount": "300000.00",
            "supplier_name": "虚构供应商", "salesperson_name": "演示销售", "signed_at": "2026-08-01",
            "location_name": "苏州演示园区", "province": "江苏省", "city": "苏州市", "deal_type": None, "source_reference": None,
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

    def fake_create(_db: object, payload: object, actor: str, _scope: object) -> dict[str, object]:
        calls.append((f"create:{actor}", payload))
        return {"id": deal_id}

    def fake_update(_db: object, received_id: UUID, payload: object, actor: str, _scope: object) -> dict[str, object]:
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

    def fake_create(_db: object, _payload: object, _actor: str, _scope: object) -> dict[str, object]:
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


def _competitor_order_payload() -> dict[str, object]:
    """构造同行与成交单位彼此独立、支持新名称建档的虚构订单。"""

    return {
        "competitor_name": "虚构新同行",
        "organization_name": "虚构新成交单位",
        "project_name": "虚构同行订单",
        "deal_type": "设备",
        "products": [{"product_name": "虚构产品", "line_total": "120000.00"}],
        "supplier_name": "虚构供应商",
        "amount": "120000.00",
        "signed_at": "2026-09-01",
        "location_name": "杭州演示园区",
        "province": "浙江省",
        "city": "杭州市",
        "source_type": "一线反馈",
        "source_reference": "虚构一线成交反馈",
        "confidence": "中",
    }


def test_admin_competitor_deal_requires_session_and_valid_parties(monkeypatch) -> None:
    """同行订单未登录返回 401，缺少独立同行字段时在服务前返回 422。"""

    with TestClient(app) as client:
        unauthorized = client.post("/api/v1/admin-deals/competitor", json=_competitor_order_payload())
    assert unauthorized.status_code == 401

    called = False

    def fake_create(_db: object, _payload: object, _actor: str, _scope: object) -> dict[str, object]:
        nonlocal called
        called = True
        return {"id": UUID(int=8)}

    payload = _competitor_order_payload()
    payload.pop("competitor_name")
    monkeypatch.setattr("app.routers.admin_deals.create_competitor_deal", fake_create)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            invalid = client.post("/api/v1/admin-deals/competitor", json=payload)
    finally:
        app.dependency_overrides.clear()
    assert invalid.status_code == 422
    assert called is False


def test_admin_competitor_deal_forwards_independent_party_names(monkeypatch) -> None:
    """同行订单成功路径把同行、正式单位名称和完整产品合同交给原子服务。"""

    captured: dict[str, object] = {}

    def fake_create(_db: object, payload: object, actor: str, _scope: object) -> dict[str, object]:
        captured.update({"payload": payload, "actor": actor})
        return {"id": UUID(int=8)}

    monkeypatch.setattr("app.routers.admin_deals.create_competitor_deal", fake_create)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/admin-deals/competitor", json=_competitor_order_payload())
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 201
    assert captured["actor"] == "admin_test"
    assert captured["payload"].competitor_name == "虚构新同行"
    assert captured["payload"].organization_name == "虚构新成交单位"
    assert captured["payload"].location_name == "杭州演示园区"
    assert len(captured["payload"].products) == 1


def test_admin_competitor_deal_accepts_missing_optional_intelligence(monkeypatch) -> None:
    """同行订单可不填写成交类型、来源类型、来源说明和置信度。"""

    captured: dict[str, object] = {}

    def fake_create(_db: object, payload: object, _actor: str, _scope: object) -> dict[str, object]:
        """保存已校验合同，确认四个缺省字段被规范化为空。"""

        captured["payload"] = payload
        return {"id": UUID(int=8)}

    payload = _competitor_order_payload()
    for field in ("deal_type", "source_type", "source_reference", "confidence"):
        payload.pop(field)
    monkeypatch.setattr("app.routers.admin_deals.create_competitor_deal", fake_create)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/admin-deals/competitor", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    parsed = captured["payload"]
    assert parsed.deal_type is None
    assert parsed.source_type is None
    assert parsed.source_reference is None
    assert parsed.confidence is None


def test_admin_competitor_deal_rejects_partial_location(monkeypatch) -> None:
    """所在地名称存在时必须同时带高德返回的省份和城市。"""

    called = False

    def fake_create(*_args: object) -> dict[str, object]:
        """记录服务是否被错误调用。"""

        nonlocal called
        called = True
        return {"id": UUID(int=8)}

    payload = _competitor_order_payload()
    payload.pop("city")
    monkeypatch.setattr("app.routers.admin_deals.create_competitor_deal", fake_create)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/admin-deals/competitor", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert called is False


def test_admin_deal_conversion_requires_admin_session() -> None:
    """未登录用户不能通过转换接口改变既有订单归属。"""

    with TestClient(app) as client:
        response = client.put(
            f"/api/v1/admin-deals/competitor/{UUID(int=8)}/convert-to-unite",
            json=_unite_order_payload(),
        )
    assert response.status_code == 401


def test_admin_deal_conversion_forwards_typed_targets(monkeypatch) -> None:
    """两种转换方向分别校验目标合同，并把原订单与操作者交给原子服务。"""

    calls: list[tuple[str, UUID, object, str]] = []
    unite_id = UUID(int=7)
    competitor_id = UUID(int=8)

    def fake_to_competitor(_db: object, received_id: UUID, payload: object, actor: str, _scope: object) -> dict[str, object]:
        calls.append(("to_competitor", received_id, payload, actor))
        return {"id": UUID(int=9)}

    def fake_to_unite(_db: object, received_id: UUID, payload: object, actor: str, _scope: object) -> dict[str, object]:
        calls.append(("to_unite", received_id, payload, actor))
        return {"id": UUID(int=10)}

    monkeypatch.setattr("app.routers.admin_deals.require_unite_deal_access", lambda *_args: None)
    monkeypatch.setattr("app.routers.admin_deals.ensure_admin_data_mutation_allowed", lambda *_args: None)
    monkeypatch.setattr("app.routers.admin_deals.convert_unite_deal_to_competitor", fake_to_competitor)
    monkeypatch.setattr("app.routers.admin_deals.convert_competitor_deal_to_unite", fake_to_unite)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            to_competitor = client.put(
                f"/api/v1/admin-deals/unite/{unite_id}/convert-to-competitor",
                json=_competitor_order_payload(),
            )
            to_unite = client.put(
                f"/api/v1/admin-deals/competitor/{competitor_id}/convert-to-unite",
                json=_unite_order_payload(),
            )
    finally:
        app.dependency_overrides.clear()
    assert to_competitor.status_code == 200
    assert to_unite.status_code == 200
    assert [(direction, deal_id, actor) for direction, deal_id, _payload, actor in calls] == [
        ("to_competitor", unite_id, "admin_test"),
        ("to_unite", competitor_id, "admin_test"),
    ]
    assert calls[0][2].competitor_name == "虚构新同行"
    assert calls[1][2].project_name == "演示订单"


def test_admin_deal_conversion_rejects_invalid_target_before_service(monkeypatch) -> None:
    """转换目标的必填字段无效时返回 422，且不触发数据库转换。"""

    called = False

    def fake_convert(*_args: object) -> dict[str, object]:
        nonlocal called
        called = True
        return {"id": UUID(int=9)}

    payload = _competitor_order_payload()
    payload.pop("competitor_name")
    monkeypatch.setattr("app.routers.admin_deals.convert_unite_deal_to_competitor", fake_convert)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.put(
                f"/api/v1/admin-deals/unite/{UUID(int=7)}/convert-to-competitor",
                json=payload,
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
    assert called is False


def test_admin_deal_rejects_partial_location_pair_before_service(monkeypatch) -> None:
    """订单所在地只填省或只填市时在输入层拒绝，避免数据库留下无法可靠授权的半份快照。"""

    called = False

    def fake_create(*_args: object) -> dict[str, object]:
        """记录无效输入是否错误进入写服务。"""

        nonlocal called
        called = True
        return {"id": UUID(int=1)}

    payload = _unite_order_payload()
    payload.pop("city")
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


def test_admin_deal_list_counts_a_database_union_before_loading_details() -> None:
    """跨归属列表先由数据库合并、按日期范围计数；空页不会加载两套完整 ORM 记录。"""

    class RecordingDb:
        """只记录计数 SQL，并返回空结果模拟无订单页面。"""

        def __init__(self) -> None:
            self.statement: object | None = None

        def scalar(self, statement: object) -> int:
            self.statement = statement
            return 0

    db = RecordingDb()
    result = list_admin_deals(
        db,  # type: ignore[arg-type]
        seller="all", supplier=None, competitor_id=None, product=None,
        year=2025, page=1, page_size=20,
    )

    sql = str(db.statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))  # type: ignore[union-attr]
    assert result.total == 0
    assert "UNION ALL" in sql
    assert "2025-01-01" in sql
    assert "2026-01-01" in sql
    assert "count" in sql.lower()
