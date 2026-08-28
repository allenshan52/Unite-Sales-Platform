"""成交订单后台路由：提供受管理员权限保护的统一筛选与优纳特订单级 CRUD。"""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.admin_deal_schemas import AdminDealFilterOptions, AdminDealMutationResult, AdminDealPage, AdminUniteDealInput
from app.database import get_db
from app.models import AdminUser
from app.services.admin_deals import create_unite_deal, delete_unite_deal, get_admin_deal_filter_options, list_admin_deals, update_unite_deal
from app.services.account_access import (
    account_data_scope,
    location_is_visible,
    require_organization_access,
    require_unite_deal_access,
)
from app.services.auth import get_current_admin

router = APIRouter(prefix="/admin-deals", tags=["成交订单后台"])


@router.post("/unite", response_model=AdminDealMutationResult, status_code=status.HTTP_201_CREATED)
def create_unite_order(
    payload: AdminUniteDealInput,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> AdminDealMutationResult:
    """在账号区域内新增一笔优纳特订单及其多产品明细。"""

    data_scope = account_data_scope(user)
    if not location_is_visible(data_scope, payload.province, payload.city):
        require_organization_access(db, payload.organization_id, data_scope)
    return create_unite_deal(db, payload, user.username)


@router.put("/unite/{deal_id}", response_model=AdminDealMutationResult)
def update_unite_order(
    deal_id: UUID,
    payload: AdminUniteDealInput,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> AdminDealMutationResult:
    """在原订单和目标区域均授权时覆盖修改全部业务字段。"""

    data_scope = account_data_scope(user)
    require_unite_deal_access(db, deal_id, data_scope)
    if not location_is_visible(data_scope, payload.province, payload.city):
        require_organization_access(db, payload.organization_id, data_scope)
    return update_unite_deal(db, deal_id, payload, user.username)


@router.delete("/unite/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unite_order(
    deal_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> None:
    """删除区域权限和二次确认均通过的一笔优纳特订单。"""

    require_unite_deal_access(db, deal_id, account_data_scope(user))
    delete_unite_deal(db, deal_id, user.username)


@router.get("/options", response_model=AdminDealFilterOptions)
def filter_options(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> AdminDealFilterOptions:
    """返回账号范围内成交订单筛选器的可选值。"""

    return get_admin_deal_filter_options(db, account_data_scope(user))


@router.get("", response_model=AdminDealPage)
def deal_list(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
    seller: Literal["all", "unite", "competitor"] = "all",
    supplier: Annotated[str | None, Query(max_length=255)] = None,
    competitor_id: UUID | None = None,
    product: Annotated[str | None, Query(max_length=255)] = None,
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=10, le=100)] = 20,
) -> AdminDealPage:
    """按账号区域、卖方、供应商、同行、产品和年份组合筛选成交订单。"""

    return list_admin_deals(
        db,
        seller=seller,
        supplier=supplier,
        competitor_id=competitor_id,
        product=product,
        year=year,
        page=page,
        page_size=page_size,
        data_scope=account_data_scope(user),
    )
