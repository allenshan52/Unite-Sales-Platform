"""同行管理 API 测试：覆盖列表、区域裁剪详情、编辑校验和认证。"""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.admin_data_schemas import CompetitorAdminListPage
from app.database import get_db
from app.main import app
from app.models import CompetitorCustomerLevel, CompetitorSiteType, IntelligenceConfidence, IntelligenceSourceType
from app.services.account_access import AccountDataScope
from app.services.admin_competitors import list_competitor_profiles
from app.services.admin_competitors import get_competitor_profile
from app.services.auth import get_current_admin


def test_admin_competitors_requires_admin_session() -> None:
    """同行聚合列表不能被匿名读取。"""

    with TestClient(app) as client:
        response = client.get("/api/v1/admin-competitors")
    assert response.status_code == 401


def _detail_payload() -> dict[str, object]:
    """构造同行订单抽屉使用的完整虚构详情响应。"""

    now = "2026-09-02T08:00:00+08:00"
    return {
        "id": str(UUID(int=801)),
        "name": "演示同行",
        "website_url": "https://example.com",
        "color": "#25846F",
        "description": "仅用于测试的虚构同行",
        "is_active": True,
        "summary": {"site_count": 1, "customer_count": 1, "linked_customer_count": 0, "deal_count": 1, "total_amount": "260000.50"},
        "sites": [],
        "customers": [],
        "scope_limited": True,
        "created_at": now,
        "updated_at": now,
    }


def test_admin_competitor_detail_requires_admin_session() -> None:
    """匿名请求不能读取或修改订单内同行档案。"""

    competitor_id = UUID(int=801)
    with TestClient(app) as client:
        detail = client.get(f"/api/v1/admin-competitors/{competitor_id}")
        updated = client.put(f"/api/v1/admin-competitors/{competitor_id}", json={
            "name": "演示同行",
            "website_url": None,
            "color": "#25846F",
            "description": None,
            "is_active": False,
        })
    assert (detail.status_code, updated.status_code) == (401, 401)


def test_admin_competitor_detail_and_update_forward_account_scope(monkeypatch) -> None:
    """详情读取与主档保存都把当前账号范围交给服务层。"""

    calls: list[tuple[str, object]] = []
    competitor_id = UUID(int=801)

    def fake_get(_db: object, received_id: UUID, scope: object) -> dict[str, object]:
        """捕获详情查询参数。"""

        calls.append(("get", (received_id, scope)))
        return _detail_payload()

    def fake_update(_db: object, received_id: UUID, payload: object, actor: str, scope: object) -> dict[str, object]:
        """捕获编辑请求和操作者。"""

        calls.append(("update", (received_id, payload, actor, scope)))
        return _detail_payload()

    monkeypatch.setattr("app.routers.admin_competitors.get_competitor_profile", fake_get)
    monkeypatch.setattr("app.routers.admin_competitors.update_competitor_profile", fake_update)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="sales_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            detail = client.get(f"/api/v1/admin-competitors/{competitor_id}")
            updated = client.put(f"/api/v1/admin-competitors/{competitor_id}", json={
                "name": "演示同行",
                "website_url": "https://example.com",
                "color": "#25846F",
                "description": "补充后的虚构资料",
                "is_active": True,
            })
    finally:
        app.dependency_overrides.clear()
    assert (detail.status_code, updated.status_code) == (200, 200)
    assert [name for name, _value in calls] == ["get", "update"]
    assert calls[1][1][2] == "sales_test"
    assert calls[1][1][1].description == "补充后的虚构资料"


def test_admin_competitor_update_rejects_invalid_profile_before_service(monkeypatch) -> None:
    """无效网址由请求模式拒绝，不进入同行保存服务。"""

    called = False

    def fake_update(*_args: object) -> dict[str, object]:
        """记录非法请求是否绕过输入校验。"""

        nonlocal called
        called = True
        return _detail_payload()

    monkeypatch.setattr("app.routers.admin_competitors.update_competitor_profile", fake_update)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="sales_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.put(f"/api/v1/admin-competitors/{UUID(int=801)}", json={
                "name": "演示同行",
                "website_url": "invalid-url",
                "color": "#25846F",
                "description": None,
                "is_active": True,
            })
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
    assert called is False


def test_admin_competitors_forwards_filters(monkeypatch) -> None:
    """路由将分页、搜索和启用状态交给聚合服务。"""

    captured: dict[str, object] = {}

    def fake_list(_db: object, **parameters: object) -> CompetitorAdminListPage:
        """捕获路由参数并返回空分页。"""

        captured.update(parameters)
        return CompetitorAdminListPage(items=[], total=0, page=2, page_size=25)

    monkeypatch.setattr("app.routers.admin_competitors.list_competitor_profiles", fake_list)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/admin-competitors?page=2&page_size=25&search=演示&is_active=true")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert {key: captured[key] for key in ("page", "page_size", "search", "is_active")} == {"page": 2, "page_size": 25, "search": "演示", "is_active": True}
    assert captured["actor_username"] == "admin_test"
    assert captured["data_scope"].unrestricted is True


def test_competitor_list_aggregates_in_fixed_batches() -> None:
    """主列表从四批子表结果组装摘要，不查询已移除的强势区域字段。"""

    competitor_id = UUID(int=801)
    now = datetime(2026, 8, 18, tzinfo=UTC)
    competitor = SimpleNamespace(
        id=competitor_id,
        name="演示同行",
        website_url="https://example.com",
        color="#25846F",
        description="仅用于测试的虚构同行",
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    class ScalarRows:
        """模拟 SQLAlchemy scalars 分页结果。"""

        def all(self) -> list[object]:
            """返回当前页同行主档。"""

            return [competitor]

    class AggregateDb:
        """按服务查询顺序返回四批同行子表统计。"""

        def __init__(self) -> None:
            self.results = iter([
                [(competitor_id, "演示总部", "北京市")],
                [(competitor_id, 4)],
                [(competitor_id, 12, 7, 2)],
                [(competitor_id, 9, Decimal("260000.50"))],
            ])

        def scalar(self, _statement: object) -> int:
            """返回符合条件的同行总数。"""

            return 1

        def scalars(self, _statement: object) -> ScalarRows:
            """返回当前分页同行。"""

            return ScalarRows()

        def execute(self, _statement: object) -> list[tuple]:
            """依次返回据点、客户和交易批量结果。"""

            return next(self.results)

    item = list_competitor_profiles(
        AggregateDb(), page=1, page_size=10, search=None, is_active=None,  # type: ignore[arg-type]
    ).items[0]
    assert item.primary_site_name == "演示总部"
    assert (item.site_count, item.customer_count, item.linked_customer_count, item.pending_link_count) == (4, 12, 7, 2)
    assert (item.deal_count, item.total_amount) == (9, Decimal("260000.50"))
    assert item.website_url == "https://example.com"
    assert "strength_region_count" not in item.model_dump()
    assert "strength_regions" not in item.model_dump()


def test_competitor_detail_only_returns_visible_order_regions() -> None:
    """区域账号只能读取覆盖范围内的据点、成交单位、订单和汇总。"""

    def deal(identifier: int, amount: str) -> SimpleNamespace:
        """构造一笔满足详情 DTO 的虚构同行订单。"""

        return SimpleNamespace(
            id=UUID(int=identifier), project_name=f"演示项目{identifier}", deal_type="设备",
            product_name=None, specification_model=None, product_image_url=None, unit_price=None,
            quantity=None, supplier_name="虚构供应商", amount=Decimal(amount), signed_at=None,
            source_type=IntelligenceSourceType.frontline, source_reference="虚构一线反馈", source_url=None,
            confidence=IntelligenceConfidence.medium, notes=None, products=[],
        )

    def customer(identifier: int, province: str, city: str, amount: str) -> SimpleNamespace:
        """构造一个带订单的虚构同行成交单位。"""

        return SimpleNamespace(
            id=UUID(int=identifier), name=f"演示单位{identifier}", customer_level=CompetitorCustomerLevel.level_three,
            address=None, province=province, city=city, longitude=None, latitude=None,
            source_type=IntelligenceSourceType.frontline, source_reference="虚构一线反馈", source_url=None,
            confidence=IntelligenceConfidence.medium, first_observed_at=None, last_verified_at=None,
            notes=None, organization_link=None, deals=[deal(identifier + 100, amount)],
        )

    def site(identifier: int, province: str, city: str) -> SimpleNamespace:
        """构造一个虚构同行据点。"""

        return SimpleNamespace(
            id=UUID(int=identifier), name=f"演示据点{identifier}", site_type=CompetitorSiteType.branch,
            address="虚构地址", province=province, city=city, longitude=120.0, latitude=30.0,
            source_type=IntelligenceSourceType.public, source_reference="虚构公开信息", source_url=None,
            confidence=IntelligenceConfidence.high, notes=None, is_primary=False,
        )

    now = datetime(2026, 9, 2, tzinfo=UTC)
    competitor = SimpleNamespace(
        id=UUID(int=801), name="演示同行", website_url=None, color="#25846F", description=None,
        is_active=False, sites=[site(811, "浙江省", "杭州市"), site(812, "广东省", "深圳市")],
        customers=[customer(821, "浙江省", "杭州市", "120000"), customer(822, "广东省", "深圳市", "88000")],
        created_at=now, updated_at=now,
    )

    class DetailDb:
        """返回同一同行对象，查询条件由服务负责构造。"""

        def scalar(self, _statement: object) -> object:
            """模拟 ORM 单记录加载。"""

            return competitor

    zhejiang_scope = AccountDataScope(False, frozenset({"浙江"}), frozenset(), frozenset())
    detail = get_competitor_profile(DetailDb(), competitor.id, zhejiang_scope)  # type: ignore[arg-type]
    assert detail.scope_limited is True
    assert [item.name for item in detail.sites] == ["演示据点811"]
    assert [item.name for item in detail.customers] == ["演示单位821"]
    assert (detail.summary.customer_count, detail.summary.deal_count, detail.summary.total_amount) == (1, 1, Decimal("120000"))

    beijing_scope = AccountDataScope(False, frozenset({"北京"}), frozenset(), frozenset())
    with pytest.raises(HTTPException) as denied:
        get_competitor_profile(DetailDb(), competitor.id, beijing_scope)  # type: ignore[arg-type]
    assert denied.value.status_code == 403
