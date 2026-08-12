"""渠道合作方服务：隔离公开地图字段，并集中处理管理员查询、校验和审计更新。"""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, ChannelPartnerLocation
from app.schemas import ChannelPartnerLocationUpdate, PublicChannelPartnerMapPoint


def list_public_channel_partner_points(db: Session) -> list[PublicChannelPartnerMapPoint]:
    """仅公开启用点的地图字段，真实坐标为空时使用演示城市中心坐标。"""

    locations = db.scalars(
        select(ChannelPartnerLocation).where(ChannelPartnerLocation.is_active.is_(True)).order_by(ChannelPartnerLocation.partner_type, ChannelPartnerLocation.name),
    ).all()
    return [
        PublicChannelPartnerMapPoint(
            id=location.id,
            name=location.name,
            partner_type=location.partner_type,
            address=location.address,
            map_longitude=location.longitude if location.longitude is not None else location.display_longitude,
            map_latitude=location.latitude if location.latitude is not None else location.display_latitude,
            coverage_radius_km=location.coverage_radius_km,
            cooperation_level=location.cooperation_level,
        )
        for location in locations
    ]


def list_channel_partner_locations(db: Session) -> list[ChannelPartnerLocation]:
    """为管理端返回完整渠道档案，包括暂时停用和敏感维护字段。"""

    return list(db.scalars(select(ChannelPartnerLocation).order_by(ChannelPartnerLocation.partner_type, ChannelPartnerLocation.name)).all())


def update_channel_partner_location(
    db: Session,
    location_id: UUID,
    payload: ChannelPartnerLocationUpdate,
    actor_username: str,
) -> ChannelPartnerLocation:
    """校验成对业务坐标后更新渠道档案，并记录被修改的字段名。"""

    location = db.get(ChannelPartnerLocation, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="未找到该渠道合作方")
    changes = payload.model_dump(exclude_unset=True)
    resulting_longitude = changes.get("longitude", location.longitude)
    resulting_latitude = changes.get("latitude", location.latitude)
    if (resulting_longitude is None) != (resulting_latitude is None):
        raise HTTPException(status_code=422, detail="经度和纬度必须同时填写或同时留空")
    for field, value in changes.items():
        setattr(location, field, value.strip() if isinstance(value, str) else value)
    db.add(AuditLog(
        organization_id=None,
        actor_username=actor_username,
        action="编辑渠道合作方",
        detail={"渠道ID": str(location.id), "字段": list(changes)},
    ))
    db.commit()
    db.refresh(location)
    return location
