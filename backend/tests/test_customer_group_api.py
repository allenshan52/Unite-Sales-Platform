"""客户集团公开 API 测试：覆盖总部首屏、详情汇总、输入校验和安全字段边界。"""

from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import OpportunityStage
from app.services.account_access import AccountDataScope
from app.services.customer_groups import build_public_customer_group_detail


def _unit(unit_id: int, name: str, *, parent_id: int | None, headquarters: bool, won: bool, stage: OpportunityStage | None) -> SimpleNamespace:
    """构造完全虚构的集团单位，集中保持汇总测试字段一致。"""

    return SimpleNamespace(
        id=UUID(int=unit_id), parent_id=UUID(int=parent_id) if parent_id else None, name=name,
        is_headquarters=headquarters, address=f"{name}演示地址",
        province="河南省" if unit_id < 3 else "上海市", city="郑州市" if unit_id < 3 else "上海市",
        longitude=113.625, latitude=34.746, is_won=won,
        actual_sales_amount=Decimal("100000.00") if won else Decimal("0.00"), opportunity_stage=stage,
        estimated_opportunity_amount=Decimal("80000.00") if stage else None,
    )


def _detail_payload() -> dict[str, object]:
    """提供前端展开集团所需的最小公开响应，不包含联系人等内部字段。"""

    return {
        "id": str(UUID(int=100)), "name": "集团1", "color": "#14845F", "headquarters_id": str(UUID(int=1)),
        "summary": {
            "branch_count": 2, "won_branch_count": 1, "active_opportunity_count": 1,
            "actual_sales_amount": "100000.00", "provinces": ["上海市", "河南省"], "cities": ["上海市", "郑州市"],
        },
        "units": [{
            "id": str(UUID(int=1)), "parent_id": None, "name": "集团1总部", "level": 0,
            "is_headquarters": True, "address": "总部演示地址", "province": "河南省", "city": "郑州市",
            "longitude": 113.625, "latitude": 34.746, "is_won": False, "actual_sales_amount": "0.00",
            "opportunity_stage": None, "estimated_opportunity_amount": None,
        }],
    }


def test_public_customer_group_headquarters_are_lazy_for_authorized_viewers(monkeypatch: pytest.MonkeyPatch, viewer_session: None) -> None:
    """首屏匿名接口只返回总部节点，不把集团分支一次性传给首页。"""

    detail = _detail_payload()
    monkeypatch.setattr(
        "app.routers.customer_groups.list_public_customer_group_headquarters",
        lambda _db, _scope: [{"id": detail["id"], "name": detail["name"], "color": detail["color"], "headquarters": detail["units"][0]}],
    )
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/customer-groups")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()[0]["headquarters"]["level"] == 0
    assert "units" not in response.json()[0]


def test_public_customer_group_detail_returns_map_tree(monkeypatch: pytest.MonkeyPatch, viewer_session: None) -> None:
    """详情接口向地图返回关系节点和后端汇总，同时保持公开字段集合收敛。"""

    monkeypatch.setattr("app.routers.customer_groups.get_public_customer_group_detail", lambda _db, _group_id, _scope: _detail_payload())
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/public/customer-groups/{UUID(int=100)}")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["actual_sales_amount"] == "100000.00"
    assert set(payload["units"][0]) == {
        "id", "parent_id", "name", "level", "is_headquarters", "address", "province", "city",
        "longitude", "latitude", "is_won", "actual_sales_amount", "opportunity_stage", "estimated_opportunity_amount",
    }


def test_public_customer_group_detail_rejects_invalid_uuid(viewer_session: None) -> None:
    """非法集团 ID 在进入数据库服务前由 FastAPI 返回输入校验错误。"""

    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/customer-groups/not-a-uuid")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


def test_customer_group_summary_and_levels_are_computed_from_units() -> None:
    """成交、活跃商机、金额和层级全部由单位记录计算，避免演示汇总漂移。"""

    group = SimpleNamespace(
        id=UUID(int=100), name="集团1", color="#14845F",
        units=[
            _unit(1, "集团1总部", parent_id=None, headquarters=True, won=False, stage=None),
            _unit(2, "集团1一级分支1", parent_id=1, headquarters=False, won=True, stage=OpportunityStage.proposal),
            _unit(3, "集团1二级分支1", parent_id=2, headquarters=False, won=False, stage=OpportunityStage.closed_lost),
        ],
    )
    detail = build_public_customer_group_detail(group)
    assert [unit.level for unit in detail.units] == [0, 1, 2]
    assert detail.summary.branch_count == 2
    assert detail.summary.won_branch_count == 1
    assert detail.summary.active_opportunity_count == 1
    assert detail.summary.actual_sales_amount == Decimal("100000.00")


def test_customer_group_detail_excludes_units_outside_account_scope() -> None:
    """河南账号只看河南集团节点，上海分支不能随整棵关系树泄露。"""

    group = SimpleNamespace(
        id=UUID(int=100), name="集团1", color="#14845F",
        units=[
            _unit(1, "集团1总部", parent_id=None, headquarters=True, won=False, stage=None),
            _unit(2, "河南分支", parent_id=1, headquarters=False, won=True, stage=OpportunityStage.proposal),
            _unit(3, "上海分支", parent_id=2, headquarters=False, won=False, stage=None),
        ],
    )

    detail = build_public_customer_group_detail(
        group,
        AccountDataScope(False, frozenset({"河南"}), frozenset(), frozenset()),
    )

    assert [unit.name for unit in detail.units] == ["集团1总部", "河南分支"]
    assert detail.summary.provinces == ["河南省"]
