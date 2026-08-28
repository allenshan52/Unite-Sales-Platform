"""销售人员聚合管理 API 测试：覆盖权限、嵌套校验、完整保存与删除合同。"""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from fastapi.testclient import TestClient

from app.admin_data_schemas import SalespersonProfileInput
from app.database import get_db
from app.main import app
from app.models import SalesActivityType, UserRole
from app.sales_coverage import SalesCoverageLevel
from app.services import admin_salespeople as admin_salespeople_service
from app.services.admin_salespeople import list_salesperson_profiles
from app.services.auth import get_current_national_user, get_current_user


def salesperson_profile_payload() -> dict[str, object]:
    """提供只含虚构信息的销售完整档案，供路由合同测试复用。"""

    return {
        "id": str(UUID(int=501)),
        "employee_code": "DEMO-X001",
        "display_name": "演示销售",
        "color": "#2878B5",
        "coverage_center_longitude": 116.4074,
        "coverage_center_latitude": 39.9042,
        "is_active": True,
        "coverage_scopes": [{"id": str(UUID(int=502)), "scope_level": "市", "scope_name": "北京市", "province": "北京", "city": "北京市", "amap_adcode": "110100"}],
        "activities": [{
            "id": str(UUID(int=503)),
            "organization_id": None,
            "organization_name": None,
            "activity_type": "拜访",
            "occurred_at": datetime(2026, 8, 17, 9, tzinfo=UTC).isoformat(),
            "province": "北京市",
            "city": "北京市",
            "amap_adcode": "110100",
            "notes": "虚构活动记录",
        }],
        "created_at": datetime(2026, 8, 17, tzinfo=UTC).isoformat(),
        "updated_at": datetime(2026, 8, 17, tzinfo=UTC).isoformat(),
    }


def test_admin_salesperson_profile_requires_session() -> None:
    """完整销售档案不能被匿名读取。"""

    with TestClient(app) as client:
        response = client.get(f"/api/v1/admin-salespeople/{UUID(int=501)}")
    assert response.status_code == 401


def test_regional_user_cannot_enter_salesperson_admin() -> None:
    """市、省或大区账号即使已登录，也不能通过直输网址访问销售数据库。"""

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        role=UserRole.employee,
        coverage_scopes=[SimpleNamespace(scope_level=SalesCoverageLevel.province, scope_name="吉林", province="吉林", city=None)],
    )
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/admin-salespeople")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403
    assert response.json()["detail"] == "当前账号没有销售数据库管理权限"


def test_admin_salesperson_list_returns_aggregated_fields(monkeypatch) -> None:
    """销售主列表一次返回城市、成交额和三类活动统计。"""

    captured: dict[str, object] = {}
    payload = {
        "items": [{
            "id": str(UUID(int=501)), "employee_code": "DEMO-X001", "display_name": "演示销售",
            "color": "#2878B5", "coverage_scopes": ["北京市（市）", "东区（大区）"], "coverage_scope_total": 2,
            "actual_sales_amount": "88000.00", "visit_count": 3, "demonstration_count": 2,
            "marketing_event_count": 1, "is_active": True,
        }],
        "total": 1, "page": 2, "page_size": 25,
    }

    def fake_list(_db: object, *, page: int, page_size: int, search: str | None) -> dict[str, object]:
        """捕获分页参数并返回聚合演示行。"""

        captured["params"] = (page, page_size, search)
        return payload

    monkeypatch.setattr("app.routers.admin_salespeople.list_salesperson_profiles", fake_list)
    app.dependency_overrides[get_current_national_user] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/admin-salespeople?page=2&page_size=25&search=演示")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["items"][0]["visit_count"] == 3
    assert response.json()["items"][0]["actual_sales_amount"] == "88000.00"
    assert captured["params"] == (2, 25, "演示")


def test_salesperson_list_aggregates_in_batches_and_caps_city_display() -> None:
    """列表聚合只保留前十个城市，同时不丢失城市总数、成交额和活动分类。"""

    salesperson_id = UUID(int=601)
    salesperson = SimpleNamespace(
        id=salesperson_id, employee_code="DEMO-X006", display_name="演示销售六",
        color="#2878B5", is_active=True,
    )

    class ScalarRows:
        """模拟 SQLAlchemy scalars 结果。"""

        def all(self) -> list[object]:
            """返回当前分页销售人员。"""

            return [salesperson]

    class AggregateDb:
        """按服务查询顺序返回城市、活动和成交三个批量结果。"""

        def __init__(self) -> None:
            self.results = iter([
                [(salesperson_id, SalesCoverageLevel.city, f"城市{index}") for index in range(1, 13)],
                [(salesperson_id, SalesActivityType.visit, 4), (salesperson_id, SalesActivityType.demonstration, 2)],
                [(salesperson_id, Decimal("128000.50"))],
            ])

        def scalar(self, _statement: object) -> int:
            """返回符合筛选的销售总数。"""

            return 1

        def scalars(self, _statement: object) -> ScalarRows:
            """返回稳定分页人员。"""

            return ScalarRows()

        def execute(self, _statement: object) -> list[tuple]:
            """依次返回三个批量聚合查询结果。"""

            return next(self.results)

    result = list_salesperson_profiles(
        AggregateDb(),  # type: ignore[arg-type]
        page=1,
        page_size=10,
        search=None,
        now=datetime(2026, 8, 17, tzinfo=UTC),
    )
    item = result.items[0]
    assert item.coverage_scopes == [f"城市{index}（市）" for index in range(1, 11)]
    assert item.coverage_scope_total == 12
    assert item.actual_sales_amount == Decimal("128000.50")
    assert (item.visit_count, item.demonstration_count, item.marketing_event_count) == (4, 2, 0)


def test_admin_salesperson_profile_rejects_invalid_nested_city() -> None:
    """市级覆盖编码在进入服务前必须满足六位数字规则。"""

    app.dependency_overrides[get_current_national_user] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/admin-salespeople", json={
                "employee_code": "DEMO-X002",
                "display_name": "演示销售二",
                "color": "#2878B5",
                "coverage_center_longitude": 116.4074,
                "coverage_center_latitude": 39.9042,
                "is_active": True,
                "coverage_scopes": [{"scope_level": "市", "scope_name": "北京市", "province": "北京", "city": "北京市", "amap_adcode": "1101"}],
                "activities": [],
            })
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
    assert "coverage_scopes" in response.text


def test_admin_salesperson_profile_crud_routes(monkeypatch) -> None:
    """认证管理员可读取、新增、原子编辑并删除销售完整档案。"""

    captured: dict[str, object] = {}
    response_payload = salesperson_profile_payload()

    def fake_get(_db: object, salesperson_id: UUID) -> dict[str, object]:
        """捕获详情 ID 并返回虚构档案。"""

        captured["get"] = salesperson_id
        return response_payload

    def fake_create(_db: object, payload: object, username: str) -> dict[str, object]:
        """捕获聚合新增输入。"""

        captured["create"] = (payload.coverage_scopes[0].city, payload.activities[0].activity_type.value, username)
        return response_payload

    def fake_update(_db: object, salesperson_id: UUID, payload: object, username: str) -> dict[str, object]:
        """捕获聚合更新输入。"""

        captured["update"] = (salesperson_id, payload.display_name, len(payload.activities), username)
        return response_payload

    def fake_delete(_db: object, salesperson_id: UUID, username: str) -> None:
        """捕获删除输入。"""

        captured["delete"] = (salesperson_id, username)

    monkeypatch.setattr("app.routers.admin_salespeople.get_salesperson_profile", fake_get)
    monkeypatch.setattr("app.routers.admin_salespeople.to_profile_read", lambda value: value)
    monkeypatch.setattr("app.routers.admin_salespeople.create_salesperson_profile", fake_create)
    monkeypatch.setattr("app.routers.admin_salespeople.update_salesperson_profile", fake_update)
    monkeypatch.setattr("app.routers.admin_salespeople.delete_salesperson_profile", fake_delete)
    app.dependency_overrides[get_current_national_user] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    request_payload = {key: value for key, value in response_payload.items() if key not in {"id", "created_at", "updated_at"}}
    request_payload["coverage_scopes"] = [{"id": str(UUID(int=502)), "scope_level": "市", "scope_name": "北京市", "province": "北京", "city": "北京市", "amap_adcode": "110100"}]
    request_payload["activities"] = [{
        "id": str(UUID(int=503)), "organization_id": None, "activity_type": "拜访",
        "occurred_at": datetime(2026, 8, 17, 9, tzinfo=UTC).isoformat(), "province": "北京市",
        "city": "北京市", "amap_adcode": "110100", "notes": "虚构活动记录",
    }]
    try:
        with TestClient(app) as client:
            get_response = client.get(f"/api/v1/admin-salespeople/{UUID(int=501)}")
            create_response = client.post("/api/v1/admin-salespeople", json=request_payload)
            update_response = client.patch(f"/api/v1/admin-salespeople/{UUID(int=501)}", json=request_payload)
            delete_response = client.delete(f"/api/v1/admin-salespeople/{UUID(int=501)}")
    finally:
        app.dependency_overrides.clear()

    assert get_response.status_code == 200
    assert create_response.status_code == 201
    assert update_response.status_code == 200
    assert delete_response.status_code == 204
    assert captured == {
        "get": UUID(int=501),
        "create": ("北京市", "拜访", "admin_test"),
        "update": (UUID(int=501), "演示销售", 1, "admin_test"),
        "delete": (UUID(int=501), "admin_test"),
    }


def test_salesperson_profile_update_syncs_linked_account_scopes(monkeypatch) -> None:
    """销售页保存覆盖范围时在提交前同步所有关联授权账号。"""

    salesperson_id = UUID(int=501)
    salesperson = SimpleNamespace(
        id=salesperson_id,
        employee_code="DEMO-X001",
        display_name="演示销售",
        color="#2878B5",
        coverage_center_longitude=116.4074,
        coverage_center_latitude=39.9042,
        is_active=True,
        coverage_scopes=[],
        activities=[],
    )
    request_payload = {
        key: value
        for key, value in salesperson_profile_payload().items()
        if key not in {"id", "created_at", "updated_at"}
    }
    request_payload["coverage_scopes"] = [{
        "scope_level": "省",
        "scope_name": "河北",
        "province": "河北",
        "city": None,
        "amap_adcode": None,
    }]
    request_payload["activities"] = []
    payload = SalespersonProfileInput.model_validate(request_payload)
    captured: dict[str, object] = {}
    db = SimpleNamespace(add=lambda _record: None)

    monkeypatch.setattr(admin_salespeople_service, "get_salesperson_profile", lambda *_args: salesperson)
    monkeypatch.setattr(admin_salespeople_service, "_sync_children", lambda *_args: None)
    monkeypatch.setattr(
        admin_salespeople_service,
        "sync_linked_account_scopes",
        lambda _db, value: captured.update(salesperson_id=value) or 2,
    )
    monkeypatch.setattr(admin_salespeople_service, "_commit_profile", lambda _db: captured.update(committed=True))
    monkeypatch.setattr(admin_salespeople_service, "to_profile_read", lambda value: value)

    result = admin_salespeople_service.update_salesperson_profile(
        db,  # type: ignore[arg-type]
        salesperson_id,
        payload,
        "admin_test",
    )

    assert result is salesperson
    assert captured == {"salesperson_id": salesperson_id, "committed": True}
