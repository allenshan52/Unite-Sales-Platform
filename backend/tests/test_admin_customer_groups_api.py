"""客户集团聚合管理 API 测试：覆盖权限、单位树校验、分页汇总与完整档案 CRUD。"""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.services.admin_customer_groups import list_customer_group_profiles
from app.services.auth import get_current_admin


def customer_group_input() -> dict[str, object]:
    """提供只含虚构信息的客户集团完整输入，供合同测试复用。"""

    return {
        "name": "演示客户集团",
        "color": "#2F8F72",
        "units": [
            {
                "draft_key": "headquarters",
                "parent_draft_key": None,
                "name": "演示集团总部",
                "is_headquarters": True,
                "address": "北京市演示路 1 号",
                "province": "北京市",
                "city": "北京市",
                "longitude": 116.4074,
                "latitude": 39.9042,
                "is_won": False,
                "actual_sales_amount": 0,
                "opportunity_stage": None,
                "estimated_opportunity_amount": None,
            },
            {
                "draft_key": "branch-1",
                "parent_draft_key": "headquarters",
                "name": "演示集团分支",
                "is_headquarters": False,
                "address": "天津市演示路 2 号",
                "province": "天津市",
                "city": "天津市",
                "longitude": 117.2,
                "latitude": 39.12,
                "is_won": True,
                "actual_sales_amount": 88000,
                "opportunity_stage": "商务谈判",
                "estimated_opportunity_amount": 120000,
            },
        ],
    }


def customer_group_response() -> dict[str, object]:
    """给虚构输入补齐服务端 ID 和时间字段，模拟完整档案响应。"""

    now = datetime(2026, 8, 18, tzinfo=UTC).isoformat()
    payload = customer_group_input()
    units = []
    ids = {"headquarters": str(UUID(int=702)), "branch-1": str(UUID(int=703))}
    for item in payload["units"]:  # type: ignore[index]
        unit = dict(item)
        unit["id"] = ids[unit["draft_key"]]
        unit["parent_draft_key"] = ids.get(unit["parent_draft_key"])
        unit["draft_key"] = unit["id"]
        unit["created_at"] = now
        unit["updated_at"] = now
        units.append(unit)
    return {"id": str(UUID(int=701)), "name": payload["name"], "color": payload["color"], "units": units, "created_at": now, "updated_at": now}


def test_admin_customer_group_profile_requires_session() -> None:
    """完整客户集团档案不能被匿名读取。"""

    with TestClient(app) as client:
        response = client.get(f"/api/v1/admin-customer-groups/{UUID(int=701)}")
    assert response.status_code == 401


def test_admin_customer_group_profile_rejects_cyclic_tree() -> None:
    """单位树在进入服务前必须拒绝循环父子关系。"""

    payload = customer_group_input()
    payload["units"][1]["parent_draft_key"] = "branch-1"  # type: ignore[index]
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/admin-customer-groups", json=payload)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
    assert "循环" in response.text


def test_customer_group_list_aggregates_in_fixed_batches() -> None:
    """集团列表从总部与聚合两批结果组装摘要，不读取每个集团的完整单位集合。"""

    group_id = UUID(int=711)
    group = SimpleNamespace(id=group_id, name="演示客户集团", color="#2F8F72")

    class ScalarRows:
        """模拟 SQLAlchemy scalars 结果。"""

        def all(self) -> list[object]:
            """返回当前分页集团主档。"""

            return [group]

    class AggregateDb:
        """按服务查询顺序返回总部和汇总两批数据。"""

        def __init__(self) -> None:
            self.results = iter([
                [(group_id, "演示集团总部", "北京市")],
                [(group_id, 12, 4, 3, Decimal("88000.50"), Decimal("120000.00"))],
            ])

        def scalar(self, _statement: object) -> int:
            """返回符合筛选的集团总数。"""

            return 1

        def scalars(self, _statement: object) -> ScalarRows:
            """返回稳定分页集团。"""

            return ScalarRows()

        def execute(self, _statement: object) -> list[tuple]:
            """依次返回总部和金额统计结果。"""

            return next(self.results)

    item = list_customer_group_profiles(AggregateDb(), page=1, page_size=10, search=None).items[0]  # type: ignore[arg-type]
    assert (item.branch_count, item.won_unit_count, item.active_opportunity_count) == (12, 4, 3)
    assert item.actual_sales_amount == Decimal("88000.50")
    assert item.estimated_opportunity_amount == Decimal("120000.00")


def test_admin_customer_group_profile_crud_routes(monkeypatch) -> None:
    """认证管理员可读取、新增、原子编辑并删除客户集团完整档案。"""

    captured: dict[str, object] = {}
    response_payload = customer_group_response()

    def fake_get(_db: object, group_id: UUID) -> dict[str, object]:
        """捕获详情 ID 并返回虚构档案。"""

        captured["get"] = group_id
        return response_payload

    def fake_create(_db: object, payload: object, username: str) -> dict[str, object]:
        """捕获完整集团新增输入。"""

        captured["create"] = (payload.name, len(payload.units), username)
        return response_payload

    def fake_update(_db: object, group_id: UUID, payload: object, username: str) -> dict[str, object]:
        """捕获完整集团更新输入。"""

        captured["update"] = (group_id, payload.units[1].parent_draft_key, username)
        return response_payload

    def fake_delete(_db: object, group_id: UUID, username: str) -> None:
        """捕获完整集团删除输入。"""

        captured["delete"] = (group_id, username)

    monkeypatch.setattr("app.routers.admin_customer_groups.get_customer_group_profile", fake_get)
    monkeypatch.setattr("app.routers.admin_customer_groups.to_profile_read", lambda item: item)
    monkeypatch.setattr("app.routers.admin_customer_groups.create_customer_group_profile", fake_create)
    monkeypatch.setattr("app.routers.admin_customer_groups.update_customer_group_profile", fake_update)
    monkeypatch.setattr("app.routers.admin_customer_groups.delete_customer_group_profile", fake_delete)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    group_id = UUID(int=701)
    try:
        with TestClient(app) as client:
            assert client.get(f"/api/v1/admin-customer-groups/{group_id}").status_code == 200
            assert client.post("/api/v1/admin-customer-groups", json=customer_group_input()).status_code == 201
            assert client.patch(f"/api/v1/admin-customer-groups/{group_id}", json=customer_group_input()).status_code == 200
            assert client.delete(f"/api/v1/admin-customer-groups/{group_id}").status_code == 204
    finally:
        app.dependency_overrides.clear()
    assert captured["create"] == ("演示客户集团", 2, "admin_test")
    assert captured["update"] == (group_id, "headquarters", "admin_test")
    assert captured["delete"] == (group_id, "admin_test")
