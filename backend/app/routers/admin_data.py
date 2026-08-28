"""管理员数据后台路由：为白名单业务表提供受认证保护的统一分页 CRUD。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.admin_data_schemas import AdminDataMutation, AdminDataOption, AdminDataPage
from app.database import get_db
from app.models import AdminUser, ChannelPartnerType
from app.services.admin_data import (
    create_admin_data,
    delete_admin_data,
    ensure_admin_data_mutation_allowed,
    list_admin_data,
    list_admin_data_options,
    update_admin_data,
    validate_admin_data,
)
from app.services.account_access import account_data_scope
from app.services.auth import get_current_admin

router = APIRouter(prefix="/admin-data", tags=["管理员数据后台"])


@router.get("/{resource}/options", response_model=list[AdminDataOption])
def resource_options(
    resource: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
    search: Annotated[str | None, Query(max_length=120)] = None,
    selected_id: UUID | None = None,
) -> list[AdminDataOption]:
    """在账号范围内搜索外键选项，防止跨区域业务名称被枚举。"""

    return list_admin_data_options(
        db,
        resource,
        search=search,
        selected_id=selected_id,
        data_scope=account_data_scope(user),
        actor_username=user.username,
    )


@router.get("/{resource}", response_model=AdminDataPage)
def list_resource(
    resource: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=10, le=100)] = 10,
    search: Annotated[str | None, Query(max_length=120)] = None,
    partner_type: ChannelPartnerType | None = None,
    parent_id: UUID | None = None,
) -> AdminDataPage:
    """分页读取账号范围内后台数据，并支持受控分类和父记录筛选。"""

    return list_admin_data(
        db,
        resource,
        page=page,
        page_size=page_size,
        search=search,
        partner_type=partner_type,
        parent_id=parent_id,
        data_scope=account_data_scope(user),
        actor_username=user.username,
    )


@router.post("/{resource}", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_resource(
    resource: str,
    payload: AdminDataMutation,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> dict:
    """校验区域权限并新增一个完整资源记录。"""

    values = validate_admin_data(resource, payload.data)
    ensure_admin_data_mutation_allowed(db, resource, None, values, account_data_scope(user), user.username)
    return create_admin_data(db, resource, values, user.username)


@router.put("/{resource}/{record_id}", response_model=dict)
def update_resource(
    resource: str,
    record_id: UUID,
    payload: AdminDataMutation,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> dict:
    """校验旧记录、目标关联和完整表单后更新资源。"""

    values = validate_admin_data(resource, payload.data)
    ensure_admin_data_mutation_allowed(db, resource, record_id, values, account_data_scope(user), user.username)
    return update_admin_data(db, resource, record_id, values, user.username)


@router.delete("/{resource}/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(
    resource: str,
    record_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> Response:
    """校验区域权限后删除资源；受外键保护的记录返回可读冲突错误。"""

    ensure_admin_data_mutation_allowed(db, resource, record_id, {}, account_data_scope(user), user.username)
    delete_admin_data(db, resource, record_id, user.username)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
