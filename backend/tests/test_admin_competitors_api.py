"""同行聚合管理 API 测试：覆盖权限、筛选透传和固定批量汇总。"""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from fastapi.testclient import TestClient

from app.admin_data_schemas import CompetitorAdminListPage
from app.database import get_db
from app.main import app
from app.services.admin_competitors import list_competitor_profiles
from app.services.auth import get_current_admin


def test_admin_competitors_requires_admin_session() -> None:
    """同行聚合列表不能被匿名读取。"""

    with TestClient(app) as client:
        response = client.get("/api/v1/admin-competitors")
    assert response.status_code == 401


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
    """主列表从五批子表结果组装摘要，不逐同行加载关系集合。"""

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
        """按服务查询顺序返回五批同行子表统计。"""

        def __init__(self) -> None:
            self.results = iter([
                [(competitor_id, "演示总部", "北京市")],
                [(competitor_id, 4)],
                [(competitor_id, 12, 7, 2)],
                [(competitor_id, 9, Decimal("260000.50"))],
                [(competitor_id, "北京市", None), (competitor_id, "江苏省", "苏州市")],
            ])

        def scalar(self, _statement: object) -> int:
            """返回符合条件的同行总数。"""

            return 1

        def scalars(self, _statement: object) -> ScalarRows:
            """返回当前分页同行。"""

            return ScalarRows()

        def execute(self, _statement: object) -> list[tuple]:
            """依次返回据点、客户、交易和区域批量结果。"""

            return next(self.results)

    item = list_competitor_profiles(
        AggregateDb(), page=1, page_size=10, search=None, is_active=None,  # type: ignore[arg-type]
    ).items[0]
    assert item.primary_site_name == "演示总部"
    assert (item.site_count, item.customer_count, item.linked_customer_count, item.pending_link_count) == (4, 12, 7, 2)
    assert (item.deal_count, item.total_amount) == (9, Decimal("260000.50"))
    assert item.website_url == "https://example.com"
    assert item.strength_regions == ["北京市", "江苏省·苏州市"]
