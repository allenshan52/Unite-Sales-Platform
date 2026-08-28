"""同行聚合管理服务：用固定批量查询生成主列表所需业务摘要。"""

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.admin_data_schemas import CompetitorAdminListItem, CompetitorAdminListPage
from app.models import (
    Competitor,
    CompetitorCustomer,
    CompetitorCustomerOrganizationLink,
    CompetitorDeal,
    CompetitorMatchStatus,
    CompetitorSite,
    CompetitorStrengthRegion,
)
from app.services.account_access import AccountDataScope, competitor_visibility_condition


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

    primary_sites = {
        competitor_id: (name, city)
        for competitor_id, name, city in db.execute(
            select(CompetitorSite.competitor_id, CompetitorSite.name, CompetitorSite.city)
            .where(CompetitorSite.competitor_id.in_(competitor_ids), CompetitorSite.is_primary.is_(True))
        )
    }
    site_counts = {
        competitor_id: site_count
        for competitor_id, site_count in db.execute(
            select(CompetitorSite.competitor_id, func.count(CompetitorSite.id))
            .where(CompetitorSite.competitor_id.in_(competitor_ids))
            .group_by(CompetitorSite.competitor_id)
        )
    }
    customer_aggregates = {
        competitor_id: (customer_count, linked_count, pending_count)
        for competitor_id, customer_count, linked_count, pending_count in db.execute(
            select(
                CompetitorCustomer.competitor_id,
                func.count(CompetitorCustomer.id),
                func.sum(case((
                    CompetitorCustomerOrganizationLink.match_status == CompetitorMatchStatus.confirmed,
                    1,
                ), else_=0)),
                func.sum(case((
                    CompetitorCustomerOrganizationLink.match_status == CompetitorMatchStatus.pending,
                    1,
                ), else_=0)),
            )
            .outerjoin(
                CompetitorCustomerOrganizationLink,
                CompetitorCustomerOrganizationLink.competitor_customer_id == CompetitorCustomer.id,
            )
            .where(CompetitorCustomer.competitor_id.in_(competitor_ids))
            .group_by(CompetitorCustomer.competitor_id)
        )
    }
    deal_aggregates = {
        competitor_id: (deal_count, total_amount)
        for competitor_id, deal_count, total_amount in db.execute(
            select(
                CompetitorCustomer.competitor_id,
                func.count(CompetitorDeal.id),
                func.coalesce(func.sum(CompetitorDeal.amount), 0),
            )
            .join(CompetitorDeal, CompetitorDeal.competitor_customer_id == CompetitorCustomer.id)
            .where(CompetitorCustomer.competitor_id.in_(competitor_ids))
            .group_by(CompetitorCustomer.competitor_id)
        )
    }
    region_labels: dict[object, list[str]] = defaultdict(list)
    for competitor_id, province, city in db.execute(
        select(
            CompetitorStrengthRegion.competitor_id,
            CompetitorStrengthRegion.province,
            CompetitorStrengthRegion.city,
        )
        .where(CompetitorStrengthRegion.competitor_id.in_(competitor_ids))
        .order_by(
            CompetitorStrengthRegion.competitor_id,
            CompetitorStrengthRegion.province,
            CompetitorStrengthRegion.city,
        )
    ):
        region_labels[competitor_id].append(f"{province}·{city}" if city else province)

    items = []
    for competitor in competitors:
        primary_site_name, primary_site_city = primary_sites.get(competitor.id, (None, None))
        customer_count, linked_count, pending_count = customer_aggregates.get(competitor.id, (0, 0, 0))
        deal_count, total_amount = deal_aggregates.get(competitor.id, (0, Decimal(0)))
        regions = region_labels.get(competitor.id, [])
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
            strength_region_count=len(regions),
            strength_regions=regions[:3],
            created_at=competitor.created_at,
            updated_at=competitor.updated_at,
        ))
    return CompetitorAdminListPage(items=items, total=total, page=page, page_size=page_size)
