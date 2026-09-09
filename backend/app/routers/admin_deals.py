"""成交订单后台路由：提供统一筛选、两类订单写入及跨归属原子转换。"""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.admin_deal_schemas import (
    AdminCompetitorDealInput,
    AdminDealFilterOptions,
    AdminDealMutationResult,
    AdminDealPage,
    AdminUniteDealInput,
)
from app.database import get_db
from app.models import AdminUser
from app.services.account_access import (
    account_data_scope,
    require_unite_deal_access,
)
from app.services.admin_data import ensure_admin_data_mutation_allowed
from app.services.admin_deals import (
    convert_competitor_deal_to_unite,
    convert_unite_deal_to_competitor,
    create_competitor_deal,
    create_unite_deal,
    delete_unite_deal,
    get_admin_deal_filter_options,
    list_admin_deals,
    update_competitor_deal,
    update_unite_deal,
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
    return create_unite_deal(db, payload, user.username, data_scope)


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
    return update_unite_deal(db, deal_id, payload, user.username, data_scope)


@router.post("/competitor", response_model=AdminDealMutationResult, status_code=status.HTTP_201_CREATED)
def create_competitor_order(
    payload: AdminCompetitorDealInput,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> AdminDealMutationResult:
    """新增同行订单，并按需建立待审核同行和成交单位主档。"""

    return create_competitor_deal(db, payload, user.username, account_data_scope(user))


@router.put("/competitor/{deal_id}", response_model=AdminDealMutationResult)
def update_competitor_order(
    deal_id: UUID,
    payload: AdminCompetitorDealInput,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> AdminDealMutationResult:
    """校验原订单区域权限后修改同行、成交单位和完整订单字段。"""

    data_scope = account_data_scope(user)
    ensure_admin_data_mutation_allowed(db, "competitor_deals", deal_id, {}, data_scope, user.username)
    return update_competitor_deal(db, deal_id, payload, user.username, data_scope)


@router.put("/unite/{deal_id}/convert-to-competitor", response_model=AdminDealMutationResult)
def convert_unite_order_to_competitor(
    deal_id: UUID,
    payload: AdminCompetitorDealInput,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> AdminDealMutationResult:
    """校验原订单权限后，把优纳特订单原子转换为同行订单。"""

    data_scope = account_data_scope(user)
    require_unite_deal_access(db, deal_id, data_scope)
    return convert_unite_deal_to_competitor(db, deal_id, payload, user.username, data_scope)


@router.put("/competitor/{deal_id}/convert-to-unite", response_model=AdminDealMutationResult)
def convert_competitor_order_to_unite(
    deal_id: UUID,
    payload: AdminUniteDealInput,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> AdminDealMutationResult:
    """校验原订单权限后，把同行订单原子转换为优纳特订单。"""

    data_scope = account_data_scope(user)
    ensure_admin_data_mutation_allowed(db, "competitor_deals", deal_id, {}, data_scope, user.username)
    return convert_competitor_deal_to_unite(db, deal_id, payload, user.username, data_scope)


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
