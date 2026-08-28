"""数据洞察 API 合同测试：覆盖授权、输入校验、聚合读取与 Excel 导出。"""

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.insights_schemas import InsightsMetric, InsightsPeriod
from app.main import app
from app.models import UserRole
from app.routers import insights as router
from app.sales_coverage import SalesCoverageLevel
from app.services.account_access import AccountDataScope
from app.services.auth import get_current_user
from app.services.insights import _region_rows


def _overview() -> dict[str, object]:
    """构造稳定的真实聚合形状，验证路由不会改写金额和区域口径。"""

    return {
        "year": 2026,
        "period": "q2",
        "metric": "sales",
        "available_years": [2026, 2025, 2024],
        "scope": {
            "level": "national", "name": "全国", "mode": "assigned",
            "visible_provinces": ["四川"], "visible_regions": ["西区"],
        },
        "aggregated_at": datetime(2026, 8, 25, tzinfo=UTC),
        "kpis": {
            "sales_amount": Decimal("3150000.00"), "sales_yoy_percent": Decimal("12.5"), "sales_qoq_percent": Decimal("4.0"),
            "project_count": 2, "projects_yoy_percent": Decimal("0.0"), "projects_qoq_percent": Decimal("0.0"),
            "average_deal_amount": Decimal("1575000.00"), "pipeline_amount": Decimal("1270000.00"),
            "pipeline_count": 2, "active_region_count": 1,
        },
        "regions": [{
            "id": "四川省", "name": "四川省", "province": "四川省", "longitude": 104.1, "latitude": 30.6,
            "sales_amount": Decimal("3150000.00"), "project_count": 2, "pipeline_amount": Decimal("1270000.00"),
            "pipeline_count": 2, "average_deal_amount": Decimal("1575000.00"), "metric_value": Decimal("3150000.00"),
            "contribution_percent": Decimal("100.0"), "rank": 1, "yoy_percent": Decimal("12.5"), "qoq_percent": Decimal("4.0"),
        }],
        "macro_regions": [{
            "id": "西区", "name": "西区", "provinces": ["四川"],
            "sales_amount": Decimal("3150000.00"), "project_count": 2,
            "pipeline_amount": Decimal("1270000.00"), "pipeline_count": 2,
            "metric_value": Decimal("3150000.00"), "contribution_percent": Decimal("100.0"),
        }],
        "trend": [{"month": month, "current_amount": Decimal("100000.00"), "previous_amount": Decimal("80000.00")} for month in range(1, 13)],
        "signals": [{"tone": "positive", "title": "四川省成交贡献居首", "description": "实际销售额占当前区域合计 100.0%。"}],
        "top_customers": [{
            "rank": 1, "name": "优纳特演示成交单位", "province": "四川省", "city": "成都市",
            "sales_amount": Decimal("3150000.00"), "project_count": 2, "latest_signed_at": date(2026, 6, 3),
        }],
        "stages": [{"stage": "商务谈判", "opportunity_count": 2, "amount": Decimal("1270000.00"), "percent": Decimal("100.0")}],
    }


def test_insights_requires_authorized_session() -> None:
    """未登录用户不能读取或导出经营金额。"""

    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/insights/overview", params={"year": 2026})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401
    assert response.json()["detail"] == "请先登录"


def test_insights_overview_and_export_success(monkeypatch: pytest.MonkeyPatch, viewer_session: None) -> None:
    """普通员工可按筛选读取聚合并下载同口径 Excel。"""

    calls: list[tuple[object, ...]] = []

    def fake_overview(_db, year, period, metric, _data_scope, scope_mode, province, city):
        calls.append((year, period.value, metric.value, scope_mode.value, province, city))
        return _overview()

    monkeypatch.setattr(router, "get_insights_overview", fake_overview)
    monkeypatch.setattr(router, "build_insights_workbook", lambda _overview_value: b"xlsx-content")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/insights/overview", params={"year": 2026, "period": "q2", "metric": "sales"})
            exported = client.get("/api/v1/public/insights/export", params={"year": 2026, "period": "q2", "metric": "sales"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == exported.status_code == 200
    assert response.json()["kpis"]["sales_amount"] == "3150000.00"
    assert response.json()["regions"][0]["contribution_percent"] == "100.0"
    assert exported.content == b"xlsx-content"
    assert exported.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert calls == [(2026, "q2", "sales", "assigned", None, None), (2026, "q2", "sales", "assigned", None, None)]


def test_insights_rejects_invalid_period_and_city_without_province(viewer_session: None) -> None:
    """非法期间与缺少省份的城市查询都在进入聚合服务前返回 422。"""

    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            invalid_period = client.get("/api/v1/public/insights/overview", params={"year": 2026, "period": "month"})
            invalid_scope = client.get("/api/v1/public/insights/overview", params={"year": 2026, "city": "成都市"})
    finally:
        app.dependency_overrides.clear()
    assert invalid_period.status_code == 422
    assert invalid_scope.status_code == 422
    assert invalid_scope.json()["detail"] == "选择城市时必须同时提供省份"


def test_insights_enforces_assigned_scope_and_expands_macro_region(monkeypatch: pytest.MonkeyPatch) -> None:
    """吉林账号不能读取范围外省份，但大区视角可读取完整北区。"""

    captured_scopes = []

    def fake_overview(_db, _year, _period, _metric, data_scope, _scope_mode, _province, _city):
        captured_scopes.append(data_scope)
        return _overview()

    user = SimpleNamespace(
        username="jilin_sales",
        role=UserRole.employee,
        coverage_scopes=[SimpleNamespace(
            scope_level=SalesCoverageLevel.province,
            scope_name="吉林",
            province="吉林",
            city=None,
        )],
    )
    monkeypatch.setattr(router, "get_insights_overview", fake_overview)
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            denied = client.get("/api/v1/public/insights/overview", params={"year": 2026, "province": "四川省"})
            assigned = client.get("/api/v1/public/insights/overview", params={"year": 2026, "province": "吉林省"})
            expanded = client.get("/api/v1/public/insights/overview", params={
                "year": 2026, "scope_mode": "region", "province": "辽宁省",
            })
    finally:
        app.dependency_overrides.clear()

    assert denied.status_code == 403
    assert assigned.status_code == expanded.status_code == 200
    assert captured_scopes[0].visible_provinces == frozenset({"吉林"})
    assert {"吉林", "辽宁", "北京", "天津"}.issubset(captured_scopes[1].visible_provinces)
    assert captured_scopes[1].regions == frozenset({"北区"})


def test_national_regions_only_include_provinces_with_current_sales() -> None:
    """全国省份列表必须排除当前期间零销售省份，即使该省仍有有效商机。"""

    query_rows = iter([
        [("四川省", Decimal("1000.00"), 1, Decimal("104.1"), Decimal("30.6"))],
        [
            ("四川省", Decimal("500.00"), 1, Decimal("104.1"), Decimal("30.6")),
            ("吉林省", Decimal("800.00"), 1, Decimal("125.3"), Decimal("43.9")),
        ],
        [],
    ])
    db = SimpleNamespace(execute=lambda _statement: SimpleNamespace(all=lambda: next(query_rows)))

    regions = _region_rows(
        db,
        year=2026,
        period=InsightsPeriod.year,
        metric=InsightsMetric.pipeline,
        province=None,
        city=None,
        data_scope=AccountDataScope(True, frozenset(), frozenset(), frozenset()),
    )

    assert [region.name for region in regions] == ["四川省"]
    assert regions[0].pipeline_amount == Decimal("500.00")
