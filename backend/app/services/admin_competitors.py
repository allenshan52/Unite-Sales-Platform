"""同行聚合管理服务：提供列表及成交订单内受区域裁剪的同行档案。"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.admin_data_schemas import (
    CompetitorAdminDetail,
    CompetitorAdminInput,
    CompetitorAdminListItem,
    CompetitorAdminListPage,
    CompetitorAdminSummary,
)
from app.models import (
    Competitor,
    CompetitorCustomer,
    CompetitorCustomerOrganizationLink,
    CompetitorDeal,
    CompetitorMatchStatus,
    CompetitorSite,
)
from app.schemas import CompetitorCustomerRead, CompetitorDealRead, CompetitorSiteRead
from app.services.account_access import (
    AccountDataScope,
    competitor_order_is_visible,
    competitor_order_location_condition,
    competitor_visibility_condition,
    location_condition,
    location_is_visible,
)
from app.services.admin_data import update_admin_data


def list_competitor_profiles(
    db: Session,
    *,
    page: int,
    page_size: int,
    search: str | None,
    is_active: bool | None,
    data_scope: AccountDataScope | None = None,
    actor_username: str | None = None,
) -> CompetitorAdminListPage:
    """分页读取账号范围内同行主档，并批量汇总据点、成交单位和交易。"""

    conditions = []
    if data_scope is not None:
        conditions.append(competitor_visibility_condition(data_scope, actor_username))
    if search and search.strip():
        keyword = f"%{search.strip()}%"
        conditions.append(or_(Competitor.name.ilike(keyword), Competitor.website_url.ilike(keyword), Competitor.description.ilike(keyword)))
    if is_active is not None:
        conditions.append(Competitor.is_active.is_(is_active))

    total = db.scalar(select(func.count(Competitor.id)).where(*conditions)) or 0
    competitors = list(db.scalars(
        select(Competitor)
        .where(*conditions)
        .order_by(Competitor.updated_at.desc(), Competitor.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all())
    competitor_ids = [competitor.id for competitor in competitors]
    if not competitor_ids:
        return CompetitorAdminListPage(items=[], total=total, page=page, page_size=page_size)

    site_scope_condition = (
        location_condition(CompetitorSite.province, CompetitorSite.city, data_scope)
        if data_scope is not None else None
    )
    customer_scope_condition = (
        location_condition(CompetitorCustomer.province, CompetitorCustomer.city, data_scope)
        if data_scope is not None else None
    )
    deal_scope_condition = competitor_order_location_condition(data_scope) if data_scope is not None else None
    primary_site_statement = (
        select(CompetitorSite.competitor_id, CompetitorSite.name, CompetitorSite.city)
        .where(CompetitorSite.competitor_id.in_(competitor_ids), CompetitorSite.is_primary.is_(True))
    )
    site_count_statement = (
        select(CompetitorSite.competitor_id, func.count(CompetitorSite.id))
        .where(CompetitorSite.competitor_id.in_(competitor_ids))
        .group_by(CompetitorSite.competitor_id)
    )
    if site_scope_condition is not None:
        primary_site_statement = primary_site_statement.where(site_scope_condition)
        site_count_statement = site_count_statement.where(site_scope_condition)
    primary_sites = {
        competitor_id: (name, city)
        for competitor_id, name, city in db.execute(primary_site_statement)
    }
    site_counts = {
        competitor_id: site_count
        for competitor_id, site_count in db.execute(site_count_statement)
    }
    customer_statement = (
        select(
            CompetitorCustomer.competitor_id,
            func.count(CompetitorCustomer.id),
            func.sum(case((CompetitorCustomerOrganizationLink.match_status == CompetitorMatchStatus.confirmed, 1), else_=0)),
            func.sum(case((CompetitorCustomerOrganizationLink.match_status == CompetitorMatchStatus.pending, 1), else_=0)),
        )
        .outerjoin(
            CompetitorCustomerOrganizationLink,
            CompetitorCustomerOrganizationLink.competitor_customer_id == CompetitorCustomer.id,
        )
        .where(CompetitorCustomer.competitor_id.in_(competitor_ids))
        .group_by(CompetitorCustomer.competitor_id)
    )
    if customer_scope_condition is not None:
        customer_statement = customer_statement.where(customer_scope_condition)
    customer_aggregates = {
        competitor_id: (customer_count, linked_count, pending_count)
        for competitor_id, customer_count, linked_count, pending_count in db.execute(customer_statement)
    }
    deal_statement = (
        select(
            CompetitorCustomer.competitor_id,
            func.count(CompetitorDeal.id),
            func.coalesce(func.sum(CompetitorDeal.amount), 0),
        )
        .join(CompetitorDeal, CompetitorDeal.competitor_customer_id == CompetitorCustomer.id)
        .where(CompetitorCustomer.competitor_id.in_(competitor_ids))
        .group_by(CompetitorCustomer.competitor_id)
    )
    if deal_scope_condition is not None:
        deal_statement = deal_statement.where(deal_scope_condition)
    deal_aggregates = {
        competitor_id: (deal_count, total_amount)
        for competitor_id, deal_count, total_amount in db.execute(deal_statement)
    }
    items = []
    for competitor in competitors:
        primary_site_name, primary_site_city = primary_sites.get(competitor.id, (None, None))
        customer_count, linked_count, pending_count = customer_aggregates.get(competitor.id, (0, 0, 0))
        deal_count, total_amount = deal_aggregates.get(competitor.id, (0, Decimal(0)))
        items.append(CompetitorAdminListItem(
            id=competitor.id,
            name=competitor.name,
            website_url=competitor.website_url,
            color=competitor.color,
            description=competitor.description,
            is_active=competitor.is_active,
            primary_site_name=primary_site_name,
            primary_site_city=primary_site_city,
            site_count=site_counts.get(competitor.id, 0),
            customer_count=customer_count or 0,
            linked_customer_count=linked_count or 0,
            pending_link_count=pending_count or 0,
            deal_count=deal_count or 0,
            total_amount=total_amount or Decimal(0),
            created_at=competitor.created_at,
            updated_at=competitor.updated_at,
        ))
    return CompetitorAdminListPage(items=items, total=total, page=page, page_size=page_size)


def _admin_customer(customer: CompetitorCustomer, deals: list[CompetitorDeal]) -> CompetitorCustomerRead:
    """把一个已通过区域过滤的成交单位连同其订单转换为管理端详情。"""

    link = customer.organization_link
    organization = link.organization if link and link.match_status is CompetitorMatchStatus.confirmed else None
    return CompetitorCustomerRead(
        id=customer.id,
        name=customer.name,
        customer_level=customer.customer_level,
        address=customer.address,
        province=customer.province,
        city=customer.city,
        longitude=customer.longitude,
        latitude=customer.latitude,
        source_type=customer.source_type,
        source_reference=customer.source_reference,
        source_url=customer.source_url,
        confidence=customer.confidence,
        first_observed_at=customer.first_observed_at,
        last_verified_at=customer.last_verified_at,
        notes=customer.notes,
        linked_organization_id=organization.id if organization else None,
        linked_organization_name=organization.name if organization else None,
        match_status=link.match_status if link else None,
        match_confidence=link.match_confidence if link else None,
        deals=[
            CompetitorDealRead.model_validate(deal, from_attributes=True)
            for deal in sorted(deals, key=lambda item: item.signed_at or date.min, reverse=True)
        ],
    )


def get_competitor_profile(
    db: Session,
    competitor_id: UUID,
    data_scope: AccountDataScope,
) -> CompetitorAdminDetail:
    """读取同行主档，并只返回账号覆盖范围内的据点、成交单位和订单。"""

    competitor = db.scalar(
        select(Competitor)
        .options(
            selectinload(Competitor.sites),
            selectinload(Competitor.customers)
            .selectinload(CompetitorCustomer.deals)
            .selectinload(CompetitorDeal.products),
            selectinload(Competitor.customers)
            .selectinload(CompetitorCustomer.organization_link)
            .selectinload(CompetitorCustomerOrganizationLink.organization),
        )
        .where(Competitor.id == competitor_id)
    )
    if competitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该同行")

    sites = [site for site in competitor.sites if location_is_visible(data_scope, site.province, site.city)]
    customer_deals = [
        (customer, [deal for deal in customer.deals if competitor_order_is_visible(data_scope, deal, customer)])
        for customer in competitor.customers
    ]
    customer_deals = [item for item in customer_deals if item[1]]
    customers = [customer for customer, _deals in customer_deals]
    visible_deals = [deal for _customer, deals in customer_deals for deal in deals]
    if not data_scope.unrestricted and not visible_deals:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号不能访问该同行的成交信息")

    return CompetitorAdminDetail(
        id=competitor.id,
        name=competitor.name,
        website_url=competitor.website_url,
        color=competitor.color,
        description=competitor.description,
        is_active=competitor.is_active,
        summary=CompetitorAdminSummary(
            site_count=len(sites),
            customer_count=len(customers),
            linked_customer_count=sum(
                customer.organization_link is not None
                and customer.organization_link.match_status is CompetitorMatchStatus.confirmed
                for customer in customers
            ),
            deal_count=len(visible_deals),
            total_amount=sum((deal.amount for deal in visible_deals), start=Decimal(0)),
        ),
        sites=[CompetitorSiteRead.model_validate(site, from_attributes=True) for site in sorted(sites, key=lambda item: (not item.is_primary, item.site_type.value, item.name))],
        customers=[
            _admin_customer(customer, deals)
            for customer, deals in sorted(customer_deals, key=lambda item: (item[0].customer_level.value, item[0].name))
        ],
        scope_limited=not data_scope.unrestricted,
        created_at=competitor.created_at,
        updated_at=competitor.updated_at,
    )


def update_competitor_profile(
    db: Session,
    competitor_id: UUID,
    payload: CompetitorAdminInput,
    actor_username: str,
    data_scope: AccountDataScope,
) -> CompetitorAdminDetail:
    """先校验可见成交订单，再保存同行主档并返回同口径详情。"""

    get_competitor_profile(db, competitor_id, data_scope)
    update_admin_data(db, "competitors", competitor_id, payload.model_dump(), actor_username)
    return get_competitor_profile(db, competitor_id, data_scope)
