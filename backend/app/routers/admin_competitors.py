"""同行聚合管理路由：提供受认证保护的同行主列表业务摘要。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.admin_data_schemas import CompetitorAdminListPage
from app.database import get_db
from app.models import AdminUser
from app.services.admin_competitors import list_competitor_profiles
from app.services.account_access import account_data_scope
from app.services.auth import get_current_admin

router = APIRouter(prefix="/admin-competitors", tags=["同行聚合管理"])


@router.get("", response_model=CompetitorAdminListPage)
def list_profiles(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=10, le=100)] = 10,
    search: Annotated[str | None, Query(max_length=120)] = None,
    is_active: bool | None = None,
) -> CompetitorAdminListPage:
    """分页返回账号范围内同行的据点、客户、交易和强势区域汇总。"""

    return list_competitor_profiles(
        db,
        page=page,
        page_size=page_size,
        search=search,
        is_active=is_active,
        data_scope=account_data_scope(user),
        actor_username=user.username,
    )
