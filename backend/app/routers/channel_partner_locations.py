"""渠道合作方路由：公开地图只读，完整档案查询和修改均要求管理员会话。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ChannelPartnerLocation
from app.schemas import ChannelPartnerLocationRead, ChannelPartnerLocationUpdate, PublicChannelPartnerMapPoint
from app.services.auth import get_current_super_admin
from app.services.channel_partner_locations import list_channel_partner_locations, list_public_channel_partner_points, update_channel_partner_location

router = APIRouter(prefix="/channel-partner-locations", tags=["渠道合作方管理"])
public_router = APIRouter(prefix="/public/channel-partner-locations", tags=["公开渠道覆盖网络"])


@public_router.get("", response_model=list[PublicChannelPartnerMapPoint])
def public_locations(db: Session = Depends(get_db)) -> list[PublicChannelPartnerMapPoint]:
    """匿名返回启用渠道的安全地图点位，不暴露合同与内部备注。"""

    return list_public_channel_partner_points(db)


@router.get("", response_model=list[ChannelPartnerLocationRead], dependencies=[Depends(get_current_super_admin)])
def admin_locations(db: Session = Depends(get_db)) -> list[ChannelPartnerLocation]:
    """管理员读取全部渠道档案，以便后续维护授权和合同信息。"""

    return list_channel_partner_locations(db)


@router.patch("/{location_id}", response_model=ChannelPartnerLocationRead)
def update_location(
    location_id: UUID,
    payload: ChannelPartnerLocationUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_super_admin),
) -> ChannelPartnerLocation:
    """把已校验渠道字段交给服务层更新并记录管理员操作。"""

    return update_channel_partner_location(db, location_id, payload, user.username)
