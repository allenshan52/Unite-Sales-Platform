"""数据洞察公开路由：向已登录主站用户提供聚合读取和 Excel 导出。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.insights_schemas import InsightsMetric, InsightsOverviewRead, InsightsPeriod, InsightsScopeMode
from app.models import AdminUser
from app.sales_coverage import canonical_province
from app.services.account_access import AccountDataScope, account_data_scope
from app.services.auth import get_current_user
from app.services.insights import get_insights_overview
from app.services.insights_exports import build_insights_workbook

public_router = APIRouter(prefix="/public/insights", tags=["数据洞察"])
YearQuery = Annotated[int, Query(ge=2000, le=2100)]
RegionQuery = Annotated[str | None, Query(min_length=2, max_length=60)]


def _validate_scope(province: str | None, city: str | None, data_scope: AccountDataScope) -> None:
    """城市统计必须同时给出省份，避免同名城市跨省混算。"""

    if city and not province:
        raise HTTPException(status_code=422, detail="选择城市时必须同时提供省份")
    if not province or data_scope.unrestricted:
        return
    normalized = canonical_province(province)
    if normalized not in data_scope.visible_provinces:
        raise HTTPException(status_code=403, detail="当前账号不能查看该区域数据")
    if city and normalized not in data_scope.provinces and (normalized, city) not in data_scope.cities:
        raise HTTPException(status_code=403, detail="当前账号不能查看该城市数据")


@public_router.get("/overview", response_model=InsightsOverviewRead)
def public_insights_overview(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_user)],
    year: YearQuery,
    period: InsightsPeriod = InsightsPeriod.year,
    metric: InsightsMetric = InsightsMetric.sales,
    scope_mode: InsightsScopeMode = InsightsScopeMode.assigned,
    province: RegionQuery = None,
    city: RegionQuery = None,
) -> InsightsOverviewRead:
    """一次返回筛选范围的 KPI、区域榜、趋势、单位榜、商机阶段与提示。"""

    data_scope = account_data_scope(user, expand_regions=scope_mode == InsightsScopeMode.region)
    _validate_scope(province, city, data_scope)
    return get_insights_overview(db, year, period, metric, data_scope, scope_mode, province, city)


@public_router.get("/export")
def public_insights_export(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_user)],
    year: YearQuery,
    period: InsightsPeriod = InsightsPeriod.year,
    metric: InsightsMetric = InsightsMetric.sales,
    scope_mode: InsightsScopeMode = InsightsScopeMode.assigned,
    province: RegionQuery = None,
    city: RegionQuery = None,
) -> StreamingResponse:
    """按与页面完全相同的筛选条件生成多工作表 Excel。"""

    data_scope = account_data_scope(user, expand_regions=scope_mode == InsightsScopeMode.region)
    _validate_scope(province, city, data_scope)
    workbook = build_insights_workbook(get_insights_overview(db, year, period, metric, data_scope, scope_mode, province, city))
    return StreamingResponse(
        iter([workbook]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="unite-data-insights.xlsx"'},
    )
