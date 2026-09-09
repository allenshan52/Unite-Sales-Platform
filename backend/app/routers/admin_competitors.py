"""同行管理路由：提供聚合列表及成交订单内的受限详情编辑。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.admin_data_schemas import CompetitorAdminDetail, CompetitorAdminInput, CompetitorAdminListPage
from app.database import get_db
from app.models import AdminUser
from app.services.admin_competitors import get_competitor_profile, list_competitor_profiles, update_competitor_profile
from app.services.account_access import account_data_scope
from app.services.auth import get_current_admin

router = APIRouter(prefix="/admin-competitors", tags=["同行聚合管理"])


@router.get("/{competitor_id}", response_model=CompetitorAdminDetail)
def get_profile(
    competitor_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> CompetitorAdminDetail:
    """按当前账号覆盖范围返回同行主档和可见成交信息。"""

    return get_competitor_profile(db, competitor_id, account_data_scope(user))


@router.put("/{competitor_id}", response_model=CompetitorAdminDetail)
def update_profile(
    competitor_id: UUID,
    payload: CompetitorAdminInput,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> CompetitorAdminDetail:
    """仅允许能看到该同行成交订单的账号修改公司主档。"""

    return update_competitor_profile(db, competitor_id, payload, user.username, account_data_scope(user))


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
