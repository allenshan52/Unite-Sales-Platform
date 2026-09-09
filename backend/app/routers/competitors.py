"""同行市场公开路由：提供十个主要据点首屏和单同行完整竞争情报。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AdminUser
from app.schemas import CompetitorDetailRead, CompetitorMapItemRead
from app.services.competitors import (
    get_public_competitor_detail,
    list_public_competitor_map_items,
)
from app.services.account_access import account_data_scope
from app.services.auth import get_current_user

public_router = APIRouter(prefix="/public/competitors", tags=["公开同行市场地图"])


@public_router.get("", response_model=list[CompetitorMapItemRead])
def public_competitor_map_items(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_user)],
) -> list[CompetitorMapItemRead]:
    """匿名返回主要据点和轻量区域，不传输成交单位、交易或内部关联。"""

    return list_public_competitor_map_items(db, account_data_scope(user))


@public_router.get("/{competitor_id}", response_model=CompetitorDetailRead)
def public_competitor_detail(
    competitor_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_user)],
) -> CompetitorDetailRead:
    """点击主要据点后返回该同行全部据点、成交单位、交易和强势区域。"""

    return get_public_competitor_detail(db, competitor_id, account_data_scope(user))
