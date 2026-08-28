"""同行市场公开查询服务：按需加载原始记录，并实时计算区域竞争强度与公开汇总。"""

from datetime import date
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Competitor,
    CompetitorCustomer,
    CompetitorCustomerOrganizationLink,
    CompetitorDeal,
    CompetitorMatchStatus,
    CompetitorRegionLevel,
    CompetitorSite,
    CompetitorSiteType,
    CompetitorStrengthLevel,
    IntelligenceConfidence,
    IntelligenceSourceType,
    Organization,
)
from app.services.account_access import AccountDataScope, competitor_visibility_condition
from app.schemas import (
    CompetitorCustomerRead,
    CompetitorDealRead,
    CompetitorDetailRead,
    CompetitorMapItemRead,
    CompetitorSiteRead,
    CompetitorStrengthRegionRead,
    CompetitorSummaryRead,
    PublicOrganizationCompetitorLinkRead,
)

REGION_SCORE_WEIGHTS = {
    "site": Decimal("0.20"),
    "customer": Decimal("0.35"),
    "amount": Decimal("0.45"),
}
SITE_TYPE_WEIGHTS = {
    CompetitorSiteType.headquarters: Decimal(3),
    CompetitorSiteType.branch: Decimal(2),
    CompetitorSiteType.service: Decimal(1),
}
REGION_LEVELS = (
    (Decimal("0.45"), CompetitorStrengthLevel.strong),
    (Decimal("0.25"), CompetitorStrengthLevel.medium),
    (Decimal("0.12"), CompetitorStrengthLevel.weak),
)


def calculate_competitor_strength_regions(competitor: Competitor) -> list[CompetitorStrengthRegionRead]:
    """按省汇总据点权重、成交单位数和交易额，生成可复算且有证据门槛的竞争区域。"""

    activities: dict[str, dict[str, object]] = {}

    def activity_for(province: str) -> dict[str, object]:
        """为同一省份复用聚合桶，防止据点与成交记录落入不同统计口径。"""

        return activities.setdefault(
            province,
            {
                "site_weight": Decimal(0),
                "site_count": 0,
                "customer_count": 0,
                "amount": Decimal(0),
            },
        )

    for site in competitor.sites:
        activity = activity_for(site.province)
        site_type = site.site_type if isinstance(site.site_type, CompetitorSiteType) else CompetitorSiteType(site.site_type)
        weight = SITE_TYPE_WEIGHTS[site_type]
        activity["site_weight"] = activity["site_weight"] + weight
        activity["site_count"] = activity["site_count"] + 1

    for customer in competitor.customers:
        activity = activity_for(customer.province)
        amount = sum((deal.amount for deal in customer.deals), start=Decimal(0))
        activity["customer_count"] = activity["customer_count"] + 1
        activity["amount"] = activity["amount"] + amount

    total_site_weight = sum((item["site_weight"] for item in activities.values()), start=Decimal(0))
    total_customer_count = sum(int(item["customer_count"]) for item in activities.values())
    total_amount = sum((item["amount"] for item in activities.values()), start=Decimal(0))
    regions: list[CompetitorStrengthRegionRead] = []

    for province, activity in activities.items():
        site_share = activity["site_weight"] / total_site_weight if total_site_weight else Decimal(0)
        customer_share = Decimal(int(activity["customer_count"])) / Decimal(total_customer_count) if total_customer_count else Decimal(0)
        amount_share = activity["amount"] / total_amount if total_amount else Decimal(0)
        score = (
            site_share * REGION_SCORE_WEIGHTS["site"]
            + customer_share * REGION_SCORE_WEIGHTS["customer"]
            + amount_share * REGION_SCORE_WEIGHTS["amount"]
        ).quantize(Decimal("0.0001"))
        strength = next((strength for threshold, strength in REGION_LEVELS if score >= threshold), None)
        if strength is None:
            continue
        site_count = int(activity["site_count"])
        customer_count = int(activity["customer_count"])
        if site_count and customer_count:
            source_type, confidence = IntelligenceSourceType.public, IntelligenceConfidence.high
        elif customer_count >= 2:
            source_type, confidence = IntelligenceSourceType.frontline, IntelligenceConfidence.medium
        else:
            source_type, confidence = IntelligenceSourceType.inferred, IntelligenceConfidence.low
        regions.append(
            CompetitorStrengthRegionRead(
                id=uuid5(NAMESPACE_URL, f"competitor-region:{competitor.id}:{province}"),
                region_level=CompetitorRegionLevel.province,
                province=province,
                city=None,
                strength_level=strength,
                source_type=source_type,
                source_reference="演示算法：同行据点、成交单位与逐笔交易记录加权汇总",
                source_url=None,
                confidence=confidence,
                basis=(
                    f"综合评分 {score * 100:.2f}%：据点占比 {site_share * 100:.1f}%、"
                    f"成交单位占比 {customer_share * 100:.1f}%、交易额占比 {amount_share * 100:.1f}%"
                ),
                score=score,
                site_count=site_count,
                customer_count=customer_count,
                total_amount=activity["amount"],
            )
        )

    strength_order = {CompetitorStrengthLevel.strong: 0, CompetitorStrengthLevel.medium: 1, CompetitorStrengthLevel.weak: 2}
    return sorted(regions, key=lambda item: (strength_order[item.strength_level], -item.score, item.province))


def _to_site(site: CompetitorSite) -> CompetitorSiteRead:
    """将据点 ORM 记录收敛为地图允许公开的字段。"""

    return CompetitorSiteRead.model_validate(site, from_attributes=True)


def _to_customer(customer: CompetitorCustomer) -> CompetitorCustomerRead:
    """组合成交单位、逐笔交易及可选正式单位关联，明确未关联状态。"""

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
        deals=[CompetitorDealRead.model_validate(deal, from_attributes=True) for deal in sorted(customer.deals, key=lambda item: item.signed_at or date.min, reverse=True)],
    )


def list_public_competitor_map_items(db: Session, data_scope: AccountDataScope) -> list[CompetitorMapItemRead]:
    """固定次数加载同行官网及主要据点，避免全国总览传输无用详情或形成 N+1。"""

    statement = (
        select(Competitor)
        .options(
            selectinload(Competitor.sites),
        )
        .where(Competitor.sites.any(CompetitorSite.is_primary.is_(True)))
        .where(Competitor.is_active.is_(True))
        .where(competitor_visibility_condition(data_scope))
        .order_by(Competitor.name)
    )
    items: list[CompetitorMapItemRead] = []
    for competitor in db.scalars(statement).all():
        primary_site = next(site for site in competitor.sites if site.is_primary)
        items.append(CompetitorMapItemRead(
            id=competitor.id,
            name=competitor.name,
            website_url=competitor.website_url,
            color=competitor.color,
            description=competitor.description,
            primary_site=_to_site(primary_site),
        ))
    return items


def build_public_competitor_detail(competitor: Competitor) -> CompetitorDetailRead:
    """从含官网的同行原始记录实时计算成交汇总和有活动证据支持的竞争区域。"""

    customers = sorted(competitor.customers, key=lambda item: (item.customer_level.value, item.name))
    deals = [deal for customer in customers for deal in customer.deals]
    strength_regions = calculate_competitor_strength_regions(competitor)
    return CompetitorDetailRead(
        id=competitor.id,
        name=competitor.name,
        website_url=competitor.website_url,
        color=competitor.color,
        description=competitor.description,
        summary=CompetitorSummaryRead(
            site_count=len(competitor.sites),
            customer_count=len(customers),
            linked_customer_count=sum(
                customer.organization_link is not None and customer.organization_link.match_status is CompetitorMatchStatus.confirmed
                for customer in customers
            ),
            deal_count=len(deals),
            total_amount=sum((deal.amount for deal in deals), start=Decimal(0)),
            strong_region_count=sum(region.strength_level is CompetitorStrengthLevel.strong for region in strength_regions),
        ),
        sites=[_to_site(site) for site in sorted(competitor.sites, key=lambda item: (not item.is_primary, item.site_type.value, item.name))],
        customers=[_to_customer(customer) for customer in customers],
        strength_regions=strength_regions,
    )


def get_public_competitor_detail(db: Session, competitor_id: UUID, data_scope: AccountDataScope) -> CompetitorDetailRead:
    """按同行 ID 延迟加载地图详情，未找到时返回统一中文错误。"""

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
        .where(
            Competitor.id == competitor_id,
            Competitor.is_active.is_(True),
            competitor_visibility_condition(data_scope),
        )
    )
    if competitor is None:
        raise HTTPException(status_code=404, detail="未找到该同行")
    return build_public_competitor_detail(competitor)


def public_organization_competitor_links(organization: Organization) -> list[PublicOrganizationCompetitorLinkRead]:
    """把已确认同行关联投影为单位数据库摘要，不返回内部匹配备注或人员字段。"""

    items: list[PublicOrganizationCompetitorLinkRead] = []
    for link in getattr(organization, "competitor_links", ()):
        if link.match_status is not CompetitorMatchStatus.confirmed:
            continue
        customer = link.competitor_customer
        items.append(
            PublicOrganizationCompetitorLinkRead(
                competitor_id=customer.competitor.id,
                competitor_name=customer.competitor.name,
                competitor_color=customer.competitor.color,
                competitor_customer_id=customer.id,
                customer_level=customer.customer_level,
                deal_count=len(customer.deals),
                total_amount=sum((deal.amount for deal in customer.deals), start=Decimal(0)),
                source_type=customer.source_type,
                confidence=customer.confidence,
                match_confidence=link.match_confidence,
            )
        )
    return sorted(items, key=lambda item: item.competitor_name)
