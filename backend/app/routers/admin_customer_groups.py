"""客户集团聚合管理路由：提供受认证保护的完整集团档案增删改查。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.admin_data_schemas import CustomerGroupAdminListPage, CustomerGroupProfileInput, CustomerGroupProfileRead
from app.database import get_db
from app.models import AdminUser
from app.services.admin_customer_groups import (
    create_customer_group_profile,
    delete_customer_group_profile,
    get_customer_group_profile,
    list_customer_group_profiles,
    to_profile_read,
    update_customer_group_profile,
)
from app.services.account_access import (
    account_data_scope,
    location_is_visible,
    require_customer_group_access,
    require_location_access,
)
from app.services.auth import get_current_admin

router = APIRouter(prefix="/admin-customer-groups", tags=["客户集团聚合管理"])


@router.get("", response_model=CustomerGroupAdminListPage)
def list_profiles(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=10, le=100)] = 10,
    search: Annotated[str | None, Query(max_length=120)] = None,
) -> CustomerGroupAdminListPage:
    """分页返回账号范围内客户集团的总部、单位、成交和商机汇总。"""

    return list_customer_group_profiles(db, page=page, page_size=page_size, search=search, data_scope=account_data_scope(user))


@router.get("/{group_id}", response_model=CustomerGroupProfileRead)
def get_profile(
    group_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> CustomerGroupProfileRead:
    """读取与账号范围有交集的客户集团主档及完整单位树。"""

    require_customer_group_access(db, group_id, account_data_scope(user))
    return to_profile_read(get_customer_group_profile(db, group_id))


@router.post("", response_model=CustomerGroupProfileRead, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: CustomerGroupProfileInput,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> CustomerGroupProfileRead:
    """一次新增至少一个节点落在账号范围内的客户集团。"""

    data_scope = account_data_scope(user)
    if not any(location_is_visible(data_scope, item.province, item.city) for item in payload.units):
        headquarters = next(item for item in payload.units if item.is_headquarters)
        require_location_access(data_scope, headquarters.province, headquarters.city)
    return create_customer_group_profile(db, payload, user.username)


@router.patch("/{group_id}", response_model=CustomerGroupProfileRead)
def update_profile(
    group_id: UUID,
    payload: CustomerGroupProfileInput,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> CustomerGroupProfileRead:
    """一次保存与账号范围有交集的客户集团主档及完整单位树。"""

    data_scope = account_data_scope(user)
    require_customer_group_access(db, group_id, data_scope)
    if not any(location_is_visible(data_scope, item.province, item.city) for item in payload.units):
        headquarters = next(item for item in payload.units if item.is_headquarters)
        require_location_access(data_scope, headquarters.province, headquarters.city)
    return update_customer_group_profile(db, group_id, payload, user.username)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    group_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> Response:
    """删除与账号范围有交集的客户集团及其全部节点。"""

    require_customer_group_access(db, group_id, account_data_scope(user))
    delete_customer_group_profile(db, group_id, user.username)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
