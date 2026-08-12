"""销售常驻点服务：集中处理公开查询、管理员列表和可追溯字段更新。"""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, SalesOfficeLocation
from app.schemas import SalesOfficeLocationUpdate


def list_public_sales_office_locations(db: Session) -> list[SalesOfficeLocation]:
    """只返回启用的常驻点，保证主站不会显示管理员暂时关闭的覆盖范围。"""

    return list(db.scalars(select(SalesOfficeLocation).where(SalesOfficeLocation.is_active.is_(True)).order_by(SalesOfficeLocation.city)).all())


def list_sales_office_locations(db: Session) -> list[SalesOfficeLocation]:
    """为管理端返回全部常驻点，包括暂时停用但仍需维护的记录。"""

    return list(db.scalars(select(SalesOfficeLocation).order_by(SalesOfficeLocation.city)).all())


def update_sales_office_location(
    db: Session,
    location_id: UUID,
    payload: SalesOfficeLocationUpdate,
    actor_username: str,
) -> SalesOfficeLocation:
    """更新一个常驻点并写入审计日志，保留管理员对地址和半径的调整轨迹。"""

    location = db.get(SalesOfficeLocation, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="未找到该销售常驻点")
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(location, field, value.strip() if isinstance(value, str) else value)
    db.add(AuditLog(
        organization_id=None,
        actor_username=actor_username,
        action="编辑销售常驻点",
        detail={"常驻点ID": str(location.id), "字段": list(changes)},
    ))
    db.commit()
    db.refresh(location)
    return location
