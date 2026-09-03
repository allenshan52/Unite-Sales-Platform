"""公司地点搜索路由：为已登录后台表单代理高德 POI Web 服务。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models import AdminUser
from app.schemas import AmapLocationSearchRead
from app.services.auth import get_current_admin
from app.services.geocoding import AmapGeocodeError, search_amap_places

router = APIRouter(prefix="/admin-location-search", tags=["管理员地点搜索"])


@router.get("", response_model=list[AmapLocationSearchRead])
def search_locations(
    keyword: Annotated[str, Query(min_length=2, max_length=120)],
    _user: Annotated[AdminUser, Depends(get_current_admin)],
) -> list[dict[str, str]]:
    """按显式关键词返回最多八个公司地点候选，并隐藏高德服务端 Key。"""

    try:
        return search_amap_places(keyword)
    except AmapGeocodeError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="高德地点搜索暂不可用，请稍后重试",
        ) from error
