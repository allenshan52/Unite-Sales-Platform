"""销售常驻点路由：公开读取启用点，并以管理员会话保护字段维护接口。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SalesOfficeLocation
from app.schemas import SalesOfficeLocationRead, SalesOfficeLocationUpdate
from app.services.auth import get_current_admin
from app.services.sales_office_locations import list_public_sales_office_locations, list_sales_office_locations, update_sales_office_location

router = APIRouter(prefix="/sales-office-locations", tags=["销售常驻点管理"])
public_router = APIRouter(prefix="/public/sales-office-locations", tags=["公开销售网络"])


@public_router.get("", response_model=list[SalesOfficeLocationRead])
def public_locations(db: Session = Depends(get_db)) -> list[SalesOfficeLocation]:
    """匿名返回启用的销售常驻点，供主站按需展示销售覆盖网络。"""

    return list_public_sales_office_locations(db)


@router.get("", response_model=list[SalesOfficeLocationRead], dependencies=[Depends(get_current_admin)])
def admin_locations(db: Session = Depends(get_db)) -> list[SalesOfficeLocation]:
    """管理员读取全部常驻点，便于后续维护停用点及其覆盖半径。"""

    return list_sales_office_locations(db)


@router.patch("/{location_id}", response_model=SalesOfficeLocationRead)
def update_location(
    location_id: UUID,
    payload: SalesOfficeLocationUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_admin),
) -> SalesOfficeLocation:
    """把已校验的常驻点字段交给服务层更新并记录管理员操作。"""

    return update_sales_office_location(db, location_id, payload, user.username)
