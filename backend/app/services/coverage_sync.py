"""销售与授权账号覆盖范围同步服务：在同一事务内维护两套范围记录的一致性。"""

from collections.abc import Iterable
from typing import Any, NoReturn
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import AdminUser, AdminUserCoverageScope, Salesperson, SalespersonCoverageScope, UserRole


SCOPE_FIELDS = ("scope_level", "scope_name", "province", "city", "amap_adcode")


def _scope_values(scope: Any) -> dict[str, Any]:
    """从 ORM 或已校验 schema 提取两类范围表共享的业务字段。"""

    return {field_name: getattr(scope, field_name) for field_name in SCOPE_FIELDS}


def _lock_salesperson(db: Session, salesperson_id: UUID) -> None:
    """锁定销售主档，让销售页与账号页的并发范围修改按顺序完成。"""

    found_id = db.scalar(
        select(Salesperson.id).where(Salesperson.id == salesperson_id).with_for_update()
    )
    if found_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="关联销售人员不存在",
        )


def _replace_linked_account_scopes(db: Session, salesperson_id: UUID) -> int:
    """把销售当前范围完整复制给所有关联普通账号，并返回同步账号数。"""

    scopes = list(db.scalars(
        select(SalespersonCoverageScope)
        .where(SalespersonCoverageScope.salesperson_id == salesperson_id)
        .order_by(SalespersonCoverageScope.scope_level, SalespersonCoverageScope.scope_name)
    ).all())
    user_ids = list(db.scalars(
        select(AdminUser.id).where(
            AdminUser.salesperson_id == salesperson_id,
            AdminUser.role == UserRole.employee,
        )
    ).all())
    if not user_ids:
        return 0

    db.execute(delete(AdminUserCoverageScope).where(AdminUserCoverageScope.user_id.in_(user_ids)))
    db.flush()
    db.add_all([
        AdminUserCoverageScope(id=uuid4(), user_id=user_id, **_scope_values(scope))
        for user_id in user_ids
        for scope in scopes
    ])
    db.flush()
    return len(user_ids)


def _raise_sync_error(db: Session, error: SQLAlchemyError) -> NoReturn:
    """回滚失败同步并把数据库异常转换为不泄露内部 SQL 的中文错误。"""

    db.rollback()
    if isinstance(error, IntegrityError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="覆盖范围同步冲突，请核对重复范围后重试",
        ) from error
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="关联账号与销售覆盖范围同步失败，请稍后重试",
    ) from error


def sync_linked_account_scopes(db: Session, salesperson_id: UUID) -> int:
    """以销售范围为准同步所有关联账号，供销售范围的全部写入入口复用。"""

    try:
        _lock_salesperson(db, salesperson_id)
        db.flush()
        return _replace_linked_account_scopes(db, salesperson_id)
    except SQLAlchemyError as error:
        _raise_sync_error(db, error)


def replace_salesperson_and_linked_account_scopes(
    db: Session,
    salesperson_id: UUID,
    scopes: Iterable[Any],
) -> int:
    """以账号页提交范围覆盖销售范围，再扇出到该销售关联的全部普通账号。"""

    try:
        _lock_salesperson(db, salesperson_id)
        db.execute(
            delete(SalespersonCoverageScope).where(
                SalespersonCoverageScope.salesperson_id == salesperson_id
            )
        )
        db.flush()
        db.add_all([
            SalespersonCoverageScope(
                id=uuid4(),
                salesperson_id=salesperson_id,
                **_scope_values(scope),
            )
            for scope in scopes
        ])
        db.flush()
        return _replace_linked_account_scopes(db, salesperson_id)
    except SQLAlchemyError as error:
        _raise_sync_error(db, error)
