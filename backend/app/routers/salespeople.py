"""销售覆盖公开路由：校验滚动月份或自然年并返回第五地图聚合数据。"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AdminUser
from app.schemas import SalespersonCoverageRead
from app.services.account_access import account_data_scope
from app.services.auth import get_current_user
from app.services.salespeople import list_public_salesperson_coverage

public_router = APIRouter(prefix="/public/salespeople", tags=["公开销售覆盖地图"])


@public_router.get("/coverage", response_model=list[SalespersonCoverageRead])
def public_salesperson_coverage(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_user)],
    response: Response,
    months: Annotated[int | None, Query(description="滚动统计月份")] = None,
    year: Annotated[int | None, Query(ge=2000, description="活动自然年")] = None,
) -> list[SalespersonCoverageRead]:
    """按单一时间口径返回授权销售 Pin，并禁止缓存请求时实时聚合结果。"""

    if months is not None and year is not None:
        raise HTTPException(status_code=422, detail="月份和年份不能同时选择")
    selected_months = 3 if months is None and year is None else months
    if selected_months is not None and selected_months not in {1, 3, 6, 12}:
        raise HTTPException(status_code=422, detail="时间范围仅支持 1、3、6 或 12 个月")
    if year is not None and year > datetime.now(UTC).year:
        raise HTTPException(status_code=422, detail="活动年份不能晚于当前年份")
    response.headers["Cache-Control"] = "no-store"
    data_scope = account_data_scope(user)
    if not data_scope.unrestricted and user.salesperson_id is None:
        return []
    return list_public_salesperson_coverage(
        db,
        selected_months,
        year=year,
        salesperson_id=None if data_scope.unrestricted else user.salesperson_id,
    )
