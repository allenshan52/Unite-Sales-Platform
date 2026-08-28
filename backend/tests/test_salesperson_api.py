"""销售覆盖公开 API 测试：覆盖默认期间、响应边界和月份输入校验。"""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import UserRole
from app.sales_coverage import SalesCoverageLevel
from app.services.auth import get_current_user
from app.services.salespeople import month_cutoff


def _coverage_payload(months: int = 3) -> list[dict[str, object]]:
    """构造完全虚构的销售地图响应，避免 API 合同测试依赖数据库。"""

    return [{
        "id": str(UUID(int=1)), "employee_code": "DEMO-S001", "display_name": "张1", "color": "#E76F51",
        "coverage_center_longitude": 120.35, "coverage_center_latitude": 31.65,
        "coverage_scopes": [{"scope_level": "大区", "scope_name": "浙江区", "province": None, "city": None, "amap_adcode": None, "included_provinces": ["浙江", "江西"]}],
        "performance": {
            "period_months": months,
            "activities": {"visits": 4, "demonstrations": 2, "marketing_events": 1, "total": 7},
            "actual_sales_amount": "320000.00", "pipeline_amount": "580000.00",
            "project_count": 1, "active_opportunity_count": 2,
        },
    }]


def test_public_salesperson_coverage_defaults_to_three_months(monkeypatch: pytest.MonkeyPatch, viewer_session: None) -> None:
    """匿名接口默认三个月，并仅暴露地图与人效所需字段。"""

    monkeypatch.setattr("app.routers.salespeople.list_public_salesperson_coverage", lambda _db, months, *, salesperson_id=None: _coverage_payload(months))
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/salespeople/coverage")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()[0]["performance"]["period_months"] == 3
    assert set(response.json()[0]) == {
        "id", "employee_code", "display_name", "color",
        "coverage_center_longitude", "coverage_center_latitude",
        "coverage_scopes", "performance",
    }


def test_public_salesperson_coverage_rejects_unsupported_months(viewer_session: None) -> None:
    """月份只能使用设计明确的 1/3/6/12，非法值在查询数据库前返回 422。"""

    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/salespeople/coverage?months=2")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


def test_regional_user_only_receives_linked_salesperson(monkeypatch: pytest.MonkeyPatch) -> None:
    """区域账号只把明确关联的销售人员 ID 交给聚合服务，避免按重叠辖区误匹配多人。"""

    linked_id = UUID(int=9)
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "app.routers.salespeople.list_public_salesperson_coverage",
        lambda _db, months, *, salesperson_id=None: captured.update(months=months, salesperson_id=salesperson_id) or _coverage_payload(months),
    )
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        role=UserRole.employee,
        salesperson_id=linked_id,
        coverage_scopes=[SimpleNamespace(scope_level=SalesCoverageLevel.province, scope_name="吉林", province="吉林", city=None)],
    )
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/salespeople/coverage?months=6")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert captured == {"months": 6, "salesperson_id": linked_id}


def test_regional_user_without_linked_salesperson_receives_no_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    """历史区域账号未关联销售人员时安全返回空列表，不得降级为查看全国。"""

    monkeypatch.setattr(
        "app.routers.salespeople.list_public_salesperson_coverage",
        lambda *_args, **_kwargs: pytest.fail("未关联的区域账号不应查询销售聚合"),
    )
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        role=UserRole.employee,
        salesperson_id=None,
        coverage_scopes=[SimpleNamespace(scope_level=SalesCoverageLevel.province, scope_name="吉林", province="吉林", city=None)],
    )
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/salespeople/coverage")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == []


def test_month_cutoff_clamps_calendar_month_end() -> None:
    """自然月回退在月末保持合法日期，避免二月窗口溢出。"""

    assert month_cutoff(datetime(2026, 3, 31, 9, tzinfo=UTC), 1) == datetime(2026, 2, 28, 9, tzinfo=UTC)
