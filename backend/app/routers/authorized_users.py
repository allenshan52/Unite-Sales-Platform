"""授权账号路由：仅超级管理员可维护普通用户及其区域覆盖范围。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AdminUser, UserRole
from app.sales_coverage import included_provinces
from app.schemas import (
    AuthorizedUserCoverageScopeRead,
    AuthorizedUserCreate,
    AuthorizedUserRead,
    AuthorizedUserUpdate,
)
from app.services.auth import get_current_super_admin
from app.services.authorized_users import (
    create_authorized_user,
    delete_authorized_user,
    list_authorized_users,
    update_authorized_user,
)

router = APIRouter(prefix="/authorized-users", tags=["授权账号"])


def _read_user(user: AdminUser, current_user_id: UUID) -> AuthorizedUserRead:
    """集中裁剪账号管理响应，确保密码和锁定内部字段永不出现在 API。"""

    salesperson = getattr(user, "salesperson", None)
    return AuthorizedUserRead(
        id=user.id,
        username=user.username,
        role=user.role,
        salesperson_id=getattr(user, "salesperson_id", None),
        salesperson_name=getattr(salesperson, "display_name", None),
        salesperson_employee_code=getattr(salesperson, "employee_code", None),
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        is_current=user.id == current_user_id,
        is_protected=user.role == UserRole.admin,
        coverage_scopes=[AuthorizedUserCoverageScopeRead(
            id=item.id,
            scope_level=item.scope_level,
            scope_name=item.scope_name,
            province=item.province,
            city=item.city,
            amap_adcode=item.amap_adcode,
            included_provinces=included_provinces(item.scope_level, item.scope_name, item.province),
        ) for item in sorted(user.coverage_scopes, key=lambda scope: (scope.scope_level.value, scope.scope_name, str(scope.id)))],
    )


@router.get("", response_model=list[AuthorizedUserRead])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[AdminUser, Depends(get_current_super_admin)],
) -> list[AuthorizedUserRead]:
    """返回管理员可维护的全部授权账号安全摘要。"""

    return [_read_user(user, current_user.id) for user in list_authorized_users(db)]


@router.post("", response_model=AuthorizedUserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AuthorizedUserCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[AdminUser, Depends(get_current_super_admin)],
) -> AuthorizedUserRead:
    """创建带至少一个覆盖范围的普通用户，并仅返回安全字段。"""

    user = create_authorized_user(db, payload.username, payload.password, payload.salesperson_id, payload.coverage_scopes)
    return _read_user(user, current_user.id)


@router.patch("/{user_id}", response_model=AuthorizedUserRead)
def update_user(
    user_id: UUID,
    payload: AuthorizedUserUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[AdminUser, Depends(get_current_super_admin)],
) -> AuthorizedUserRead:
    """修改普通用户启用状态和全部范围，超级管理员保护规则由服务层兜底。"""

    user = update_authorized_user(
        db,
        user_id,
        is_active=payload.is_active,
        salesperson_id=payload.salesperson_id,
        coverage_scopes=payload.coverage_scopes,
    )
    return _read_user(user, current_user.id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[AdminUser, Depends(get_current_super_admin)],
) -> Response:
    """二次确认由前端收集，服务端继续执行不可绕过的管理员保留规则。"""

    delete_authorized_user(db, user_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
