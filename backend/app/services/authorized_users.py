"""授权账号管理服务：由超级管理员维护普通用户、状态和四级数据覆盖范围。"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import AdminSession, AdminUser, AdminUserCoverageScope, Salesperson, UserRole
from app.schemas import AuthorizedUserCoverageScopeInput
from app.services.auth import password_hasher
from app.services.coverage_sync import replace_salesperson_and_linked_account_scopes


def list_authorized_users(db: Session) -> list[AdminUser]:
    """按角色和用户名稳定返回账号及范围，不加载密码或会话关系。"""

    return list(db.scalars(
        select(AdminUser)
        .options(selectinload(AdminUser.coverage_scopes), joinedload(AdminUser.salesperson))
        .order_by(AdminUser.role.desc(), AdminUser.username)
    ).all())


def _scope_records(scopes: list[AuthorizedUserCoverageScopeInput]) -> list[AdminUserCoverageScope]:
    """把已校验输入转换为新的 ORM 子记录，账号 ID 由关系自动填充。"""

    return [AdminUserCoverageScope(**scope.model_dump()) for scope in scopes]


def _validate_salesperson(db: Session, salesperson_id: UUID | None) -> None:
    """拒绝关联不存在的销售人员，避免账号登录后无法获得自己的 Pin。"""

    if salesperson_id is not None and db.scalar(select(Salesperson.id).where(Salesperson.id == salesperson_id)) is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="关联销售人员不存在")


def _get_authorized_user(db: Session, user_id: UUID, *, for_update: bool = False) -> AdminUser:
    """按需锁定账号主行并分批预加载可空销售关系，避免 PostgreSQL 锁定外连接失败。"""

    statement = select(AdminUser).options(
        selectinload(AdminUser.coverage_scopes),
        selectinload(AdminUser.salesperson),
    ).where(AdminUser.id == user_id)
    if for_update:
        statement = statement.with_for_update()
    user = db.scalar(statement)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="授权账号不存在")
    return user


def create_authorized_user(
    db: Session,
    username: str,
    password: str,
    salesperson_id: UUID | None,
    coverage_scopes: list[AuthorizedUserCoverageScopeInput],
) -> AdminUser:
    """创建普通账号；有关联销售时，把提交范围同步到销售及其全部账号。"""

    _validate_salesperson(db, salesperson_id)
    user = AdminUser(
        username=username.strip(),
        salesperson_id=salesperson_id,
        password_hash=password_hasher.hash(password),
        role=UserRole.employee,
    )
    try:
        db.add(user)
        if salesperson_id is None:
            user.coverage_scopes.extend(_scope_records(coverage_scopes))
        else:
            replace_salesperson_and_linked_account_scopes(db, salesperson_id, coverage_scopes)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在") from exc
    db.refresh(user)
    return _get_authorized_user(db, user.id)


def update_authorized_user(
    db: Session,
    user_id: UUID,
    *,
    is_active: bool,
    salesperson_id: UUID | None,
    coverage_scopes: list[AuthorizedUserCoverageScopeInput],
) -> AdminUser:
    """原子替换普通账号状态；有关联销售时双向统一该销售的全部账号范围。"""

    target = _get_authorized_user(db, user_id, for_update=True)
    if target.role == UserRole.admin:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="超级管理员账号受保护，不能修改")
    _validate_salesperson(db, salesperson_id)
    target.is_active = is_active
    target.salesperson_id = salesperson_id
    try:
        if salesperson_id is None:
            target.coverage_scopes.clear()
            db.flush()
            target.coverage_scopes.extend(_scope_records(coverage_scopes))
        else:
            replace_salesperson_and_linked_account_scopes(db, salesperson_id, coverage_scopes)
        if not is_active:
            db.execute(delete(AdminSession).where(AdminSession.user_id == target.id))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="账号覆盖范围重复") from exc
    return _get_authorized_user(db, target.id)


def delete_authorized_user(db: Session, user_id: UUID, current_user_id: UUID) -> None:
    """删除普通账号及其会话，同时禁止删除当前账号或唯一超级管理员。"""

    target = _get_authorized_user(db, user_id, for_update=True)
    if target.id == current_user_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="不能删除当前登录账号")
    if target.role == UserRole.admin:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="超级管理员账号受保护，不能删除")
    db.delete(target)
    db.commit()
