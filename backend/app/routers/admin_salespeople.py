"""销售人员聚合管理路由：提供受认证保护的完整档案增删改查。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.admin_data_schemas import SalespersonAdminListPage, SalespersonProfileInput, SalespersonProfileRead
from app.database import get_db
from app.models import AdminUser
from app.services.admin_salespeople import (
    create_salesperson_profile,
    delete_salesperson_profile,
    get_salesperson_profile,
    list_salesperson_profiles,
    to_profile_read,
    update_salesperson_profile,
)
from app.services.auth import get_current_national_user

router = APIRouter(prefix="/admin-salespeople", tags=["销售人员聚合管理"])


@router.get("", response_model=SalespersonAdminListPage)
def list_profiles(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AdminUser, Depends(get_current_national_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=10, le=100)] = 10,
    search: Annotated[str | None, Query(max_length=120)] = None,
) -> SalespersonAdminListPage:
    """分页返回销售人员列表所需的覆盖范围、成交和近三个月活动汇总。"""

    return list_salesperson_profiles(db, page=page, page_size=page_size, search=search)


@router.get("/{salesperson_id}", response_model=SalespersonProfileRead)
def get_profile(
    salesperson_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AdminUser, Depends(get_current_national_user)],
) -> SalespersonProfileRead:
    """读取销售人员主档及其分级覆盖范围、活动流水。"""

    return to_profile_read(get_salesperson_profile(db, salesperson_id))


@router.post("", response_model=SalespersonProfileRead, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: SalespersonProfileInput,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_national_user)],
) -> SalespersonProfileRead:
    """一次新增与账号区域有交集的销售人员主档及全部内嵌记录。"""

    return create_salesperson_profile(db, payload, user.username)


@router.patch("/{salesperson_id}", response_model=SalespersonProfileRead)
def update_profile(
    salesperson_id: UUID,
    payload: SalespersonProfileInput,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_national_user)],
) -> SalespersonProfileRead:
    """旧档案和新范围均与账号区域相交时保存两个完整子集合。"""

    return update_salesperson_profile(db, salesperson_id, payload, user.username)


@router.delete("/{salesperson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    salesperson_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_national_user)],
) -> Response:
    """删除与账号区域有交集的销售档案，保留其他业务引用保护。"""

    delete_salesperson_profile(db, salesperson_id, user.username)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
