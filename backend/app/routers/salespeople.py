"""销售覆盖公开路由：校验月份范围并返回第五地图所需的聚合数据。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
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
    months: Annotated[int, Query(description="滚动统计月份")] = 3,
) -> list[SalespersonCoverageRead]:
    """区域账号只返回其关联销售 Pin，全国账号与超管返回全部销售。"""

    if months not in {1, 3, 6, 12}:
        raise HTTPException(status_code=422, detail="时间范围仅支持 1、3、6 或 12 个月")
    data_scope = account_data_scope(user)
    if not data_scope.unrestricted and user.salesperson_id is None:
        return []
    return list_public_salesperson_coverage(
        db,
        months,
        salesperson_id=None if data_scope.unrestricted else user.salesperson_id,
    )
