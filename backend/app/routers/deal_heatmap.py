"""成交金额热力图公开路由：提供卖方选择、省级汇总和点击省份详情。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AdminUser
from app.heatmap_schemas import (
    DealHeatmapProvinceDetailRead,
    DealHeatmapSellerRead,
    DealHeatmapSummaryRead,
)
from app.services.deal_heatmap import (
    get_deal_heatmap_province_detail,
    get_deal_heatmap_summary,
    list_deal_heatmap_sellers,
)
from app.services.account_access import account_data_scope
from app.services.auth import get_current_user

public_router = APIRouter(prefix="/public/deal-heatmap", tags=["成交金额热力图"])
SellerQuery = Annotated[str, Query(min_length=1, max_length=36)]
ProvincePath = Annotated[str, Path(min_length=2, max_length=60)]
YearQuery = Annotated[int | None, Query(ge=2000, le=2100)]


@public_router.get("/sellers", response_model=list[DealHeatmapSellerRead])
def public_deal_heatmap_sellers(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_user)],
) -> list[DealHeatmapSellerRead]:
    """返回优纳特及启用同行，供公司下拉菜单使用。"""

    return list_deal_heatmap_sellers(db, account_data_scope(user))


@public_router.get("/provinces", response_model=DealHeatmapSummaryRead)
def public_deal_heatmap_summary(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_user)],
    seller_id: SellerQuery = "unite",
    year: YearQuery = None,
) -> DealHeatmapSummaryRead:
    """返回当前卖方全部或指定年份成交额，并独立附加有效采购意向。"""

    return get_deal_heatmap_summary(db, seller_id, year, account_data_scope(user))


@public_router.get("/provinces/{province}", response_model=DealHeatmapProvinceDetailRead)
def public_deal_heatmap_province_detail(
    province: ProvincePath,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_user)],
    seller_id: SellerQuery = "unite",
    year: YearQuery = None,
) -> DealHeatmapProvinceDetailRead:
    """点击省份时按需返回同年份逐笔成交和当前采购意向。"""

    return get_deal_heatmap_province_detail(db, seller_id, province, year, account_data_scope(user))
