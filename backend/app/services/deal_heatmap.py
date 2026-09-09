"""成交金额热力图查询服务：按可选年份聚合优纳特、同行成交与有效采购意向。"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, exists, func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.heatmap_schemas import (
    DealHeatmapIntentionRead,
    DealHeatmapOrderRead,
    DealHeatmapProvinceDetailRead,
    DealHeatmapProvinceRead,
    DealHeatmapSellerRead,
    DealHeatmapSummaryRead,
)
from app.models import (
    Competitor,
    CompetitorCustomer,
    CompetitorDeal,
    Opportunity,
    OpportunityStage,
    Organization,
    OrganizationSite,
    SalesProject,
)
from app.sales_coverage import canonical_province
from app.services.account_access import AccountDataScope, competitor_visibility_condition, location_condition

UNITE_SELLER_ID = "unite"


def list_deal_heatmap_sellers(db: Session, data_scope: AccountDataScope | None = None) -> list[DealHeatmapSellerRead]:
    """优纳特固定置顶，其后列出启用同行及其可空官网。"""

    if data_scope is None:
        data_scope = AccountDataScope(True, frozenset(), frozenset(), frozenset())
    competitors = db.execute(
        select(Competitor.id, Competitor.name, Competitor.website_url)
        .where(Competitor.is_active.is_(True), competitor_visibility_condition(data_scope))
        .order_by(Competitor.name)
    ).all()
    return [
        DealHeatmapSellerRead(id=UNITE_SELLER_ID, name="优纳特", kind="unite"),
        *(
            DealHeatmapSellerRead(id=str(competitor_id), name=name, kind="competitor", website_url=website_url)
            for competitor_id, name, website_url in competitors
        ),
    ]


def _resolve_seller(
    db: Session,
    seller_id: str,
    data_scope: AccountDataScope | None = None,
) -> tuple[DealHeatmapSellerRead, UUID | None]:
    """把公开卖方键解析为优纳特或带官网的启用同行，并统一错误。"""

    if seller_id == UNITE_SELLER_ID:
        return DealHeatmapSellerRead(id=UNITE_SELLER_ID, name="优纳特", kind="unite"), None
    if data_scope is None:
        data_scope = AccountDataScope(True, frozenset(), frozenset(), frozenset())
    try:
        competitor_id = UUID(seller_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail="公司参数无效") from error
    competitor = db.execute(
        select(Competitor.id, Competitor.name, Competitor.website_url)
        .where(
            Competitor.id == competitor_id,
            Competitor.is_active.is_(True),
            competitor_visibility_condition(data_scope),
        )
    ).one_or_none()
    if competitor is None:
        raise HTTPException(status_code=404, detail="未找到该同行公司")
    return DealHeatmapSellerRead(
        id=str(competitor.id),
        name=competitor.name,
        kind="competitor",
        website_url=competitor.website_url,
    ), competitor.id


def _filter_signed_year(statement, signed_at_column, year: int | None):
    """只在选择年份时追加左闭右开日期边界，空年份保持历史全量口径。"""

    if year is None:
        return statement
    return statement.where(signed_at_column >= date(year, 1, 1), signed_at_column < date(year + 1, 1, 1))


def _available_years(
    db: Session,
    competitor_id: UUID | None,
    data_scope: AccountDataScope | None = None,
) -> list[int]:
    """按当前卖方可见成交返回降序年份；优纳特保持全国口径。"""

    if competitor_id is None:
        statement = (
            select(func.extract("year", SalesProject.signed_at))
            .select_from(SalesProject)
            .join(Organization, Organization.id == SalesProject.organization_id)
            .join(
                OrganizationSite,
                and_(OrganizationSite.organization_id == Organization.id, OrganizationSite.is_primary.is_(True)),
            )
            .where(
                Organization.archived_at.is_(None),
                OrganizationSite.province.is_not(None),
                SalesProject.contract_amount > 0,
                SalesProject.signed_at.is_not(None),
            )
        )
    else:
        statement = (
            select(func.extract("year", CompetitorDeal.signed_at))
            .select_from(CompetitorDeal)
            .join(CompetitorCustomer, CompetitorCustomer.id == CompetitorDeal.competitor_customer_id)
            .where(
                CompetitorCustomer.competitor_id == competitor_id,
                CompetitorCustomer.province.is_not(None),
                CompetitorDeal.amount > 0,
                CompetitorDeal.signed_at.is_not(None),
            )
        )
        if data_scope is not None:
            statement = statement.where(location_condition(
                CompetitorCustomer.province, CompetitorCustomer.city, data_scope,
            ))
    values = db.execute(statement.distinct().order_by(statement.selected_columns[0].desc())).scalars().all()
    return [int(value) for value in values]


def _signed_summary_rows(
    db: Session,
    competitor_id: UUID | None,
    year: int | None,
    data_scope: AccountDataScope | None = None,
) -> list[tuple[str, int, Decimal]]:
    """按卖方、年份和同行账号范围聚合实际成交；优纳特保持全国。"""

    if competitor_id is None:
        statement = (
            select(
                OrganizationSite.province,
                func.count(SalesProject.id),
                func.coalesce(func.sum(SalesProject.contract_amount), 0),
            )
            .select_from(SalesProject)
            .join(Organization, Organization.id == SalesProject.organization_id)
            .join(
                OrganizationSite,
                and_(OrganizationSite.organization_id == Organization.id, OrganizationSite.is_primary.is_(True)),
            )
            .where(
                Organization.archived_at.is_(None),
                OrganizationSite.province.is_not(None),
                SalesProject.contract_amount > 0,
            )
            .group_by(OrganizationSite.province)
        )
    else:
        statement = (
            select(
                CompetitorCustomer.province,
                func.count(CompetitorDeal.id),
                func.coalesce(func.sum(CompetitorDeal.amount), 0),
            )
            .select_from(CompetitorDeal)
            .join(CompetitorCustomer, CompetitorCustomer.id == CompetitorDeal.competitor_customer_id)
            .where(CompetitorCustomer.competitor_id == competitor_id, CompetitorDeal.amount > 0)
            .group_by(CompetitorCustomer.province)
        )
        if data_scope is not None:
            statement = statement.where(location_condition(
                CompetitorCustomer.province, CompetitorCustomer.city, data_scope,
            ))
    signed_at_column = SalesProject.signed_at if competitor_id is None else CompetitorDeal.signed_at
    statement = _filter_signed_year(statement, signed_at_column, year)
    return [(province, int(count), Decimal(amount)) for province, count, amount in db.execute(statement).all()]


def active_opportunity_statement():
    """复用有效意向边界：排除失单、已转成交、归档单位和空金额。"""

    converted = exists(select(SalesProject.id).where(SalesProject.opportunity_id == Opportunity.id))
    return (
        select(Opportunity, Organization.name, OrganizationSite.province)
        .join(Organization, Organization.id == Opportunity.organization_id)
        .join(
            OrganizationSite,
            and_(OrganizationSite.organization_id == Organization.id, OrganizationSite.is_primary.is_(True)),
        )
        .where(
            Organization.archived_at.is_(None),
            OrganizationSite.province.is_not(None),
            Opportunity.stage != OpportunityStage.closed_lost,
            Opportunity.estimated_amount.is_not(None),
            Opportunity.estimated_amount > 0,
            ~converted,
        )
    )


def _intention_summary_rows(
    db: Session,
    data_scope: AccountDataScope | None = None,
) -> list[tuple[str, int, Decimal]]:
    """从有效意向生成省级汇总；同行对比层只保留账号负责范围。"""

    statement = active_opportunity_statement().with_only_columns(
        OrganizationSite.province,
        func.count(Opportunity.id),
        func.coalesce(func.sum(Opportunity.estimated_amount), 0),
    ).group_by(OrganizationSite.province)
    if data_scope is not None:
        statement = statement.where(location_condition(
            OrganizationSite.province, OrganizationSite.city, data_scope,
        ))
    return [(province, int(count), Decimal(amount)) for province, count, amount in db.execute(statement).all()]


def get_deal_heatmap_summary(
    db: Session,
    seller_id: str,
    year: int | None = None,
    data_scope: AccountDataScope | None = None,
) -> DealHeatmapSummaryRead:
    """合并当前卖方同年份成交和当前采购意向，保留两个独立指标。"""

    if data_scope is None:
        data_scope = AccountDataScope(True, frozenset(), frozenset(), frozenset())
    seller, competitor_id = _resolve_seller(db, seller_id, data_scope)
    provinces: dict[str, DealHeatmapProvinceRead] = {}
    competitor_scope = data_scope if competitor_id is not None else None
    for province, count, amount in _signed_summary_rows(db, competitor_id, year, competitor_scope):
        provinces[province] = DealHeatmapProvinceRead(
            province=province,
            signed_amount=amount,
            signed_order_count=count,
            intention_amount=Decimal(0),
            intention_count=0,
        )
    for province, count, amount in _intention_summary_rows(db, competitor_scope):
        summary = provinces.setdefault(
            province,
            DealHeatmapProvinceRead(
                province=province,
                signed_amount=Decimal(0),
                signed_order_count=0,
                intention_amount=Decimal(0),
                intention_count=0,
            ),
        )
        summary.intention_amount = amount
        summary.intention_count = count
    return DealHeatmapSummaryRead(
        seller=seller,
        available_years=_available_years(db, competitor_id, competitor_scope),
        provinces=sorted(provinces.values(), key=lambda item: (-item.signed_amount, item.province)),
    )


def _signed_orders(
    db: Session,
    province: str,
    competitor_id: UUID | None,
    year: int | None,
    data_scope: AccountDataScope | None = None,
) -> list[DealHeatmapOrderRead]:
    """按省与年份读取逐笔成交；同行额外应用账号城市/省份范围。"""

    if competitor_id is None:
        statement = (
            select(SalesProject, Organization.name)
            .join(Organization, Organization.id == SalesProject.organization_id)
            .join(
                OrganizationSite,
                and_(OrganizationSite.organization_id == Organization.id, OrganizationSite.is_primary.is_(True)),
            )
            .where(
                Organization.archived_at.is_(None),
                OrganizationSite.province == province,
                SalesProject.contract_amount > 0,
            )
        )
        rows = db.execute(
            _filter_signed_year(statement, SalesProject.signed_at, year)
            .order_by(SalesProject.signed_at.desc().nullslast(), SalesProject.name)
        ).all()
        return [
            DealHeatmapOrderRead(
                id=project.id,
                customer_name=customer_name,
                project_name=project.name,
                amount=project.contract_amount,
                signed_at=project.signed_at,
            )
            for project, customer_name in rows
        ]
    statement = (
        select(
            CompetitorDeal,
            CompetitorCustomer.name,
            CompetitorCustomer.province,
            CompetitorCustomer.city,
        )
        .options(selectinload(CompetitorDeal.products))
        .join(CompetitorCustomer, CompetitorCustomer.id == CompetitorDeal.competitor_customer_id)
        .where(
            CompetitorCustomer.competitor_id == competitor_id,
            CompetitorCustomer.province == province,
            CompetitorDeal.amount > 0,
        )
    )
    if data_scope is not None:
        statement = statement.where(location_condition(
            CompetitorCustomer.province, CompetitorCustomer.city, data_scope,
        ))
    rows = db.execute(
        _filter_signed_year(statement, CompetitorDeal.signed_at, year)
        .order_by(CompetitorDeal.signed_at.desc().nullslast(), CompetitorDeal.project_name)
    ).all()
    return [
        DealHeatmapOrderRead(
            id=deal.id,
            customer_name=customer_name,
            customer_province=customer_province,
            customer_city=customer_city,
            project_name=deal.project_name,
            amount=deal.amount,
            signed_at=deal.signed_at,
            deal_type=deal.deal_type,
            products=[
                {
                    "id": product.id,
                    "product_name": product.product_name,
                    "brand": product.brand,
                    "specification_model": product.specification_model,
                    "product_image_url": product.product_image_url,
                    "unit_price": product.unit_price,
                    "quantity": product.quantity,
                    "line_total": product.line_total,
                }
                for product in getattr(deal, "products", [])
            ],
            product_name=getattr(deal, "product_name", None),
            specification_model=getattr(deal, "specification_model", None),
            product_image_url=getattr(deal, "product_image_url", None),
            unit_price=getattr(deal, "unit_price", None),
            quantity=getattr(deal, "quantity", None),
            supplier_name=deal.supplier_name,
            source_type=deal.source_type,
            source_reference=deal.source_reference,
            source_url=deal.source_url,
            confidence=deal.confidence,
            notes=deal.notes,
        )
        for deal, customer_name, customer_province, customer_city in rows
    ]


def _province_intentions(
    db: Session,
    province: str,
    data_scope: AccountDataScope | None = None,
) -> list[DealHeatmapIntentionRead]:
    """按省返回有效采购意向；同行对比层同时限制账号负责城市。"""

    statement = active_opportunity_statement().where(OrganizationSite.province == province)
    if data_scope is not None:
        statement = statement.where(location_condition(
            OrganizationSite.province, OrganizationSite.city, data_scope,
        ))
    rows = db.execute(
        statement
        .order_by(Opportunity.next_action_at.asc().nullslast(), Opportunity.title)
    ).all()
    return [
        DealHeatmapIntentionRead(
            id=opportunity.id,
            customer_name=customer_name,
            title=opportunity.title,
            stage=opportunity.stage,
            estimated_amount=opportunity.estimated_amount,
            next_action_at=opportunity.next_action_at,
        )
        for opportunity, customer_name, _province in rows
    ]


def get_deal_heatmap_province_detail(
    db: Session,
    seller_id: str,
    province: str,
    year: int | None = None,
    data_scope: AccountDataScope | None = None,
) -> DealHeatmapProvinceDetailRead:
    """按点击省份与年份懒加载成交与意向明细，避免首屏传输全国订单。"""

    if data_scope is None:
        data_scope = AccountDataScope(True, frozenset(), frozenset(), frozenset())
    seller, competitor_id = _resolve_seller(db, seller_id, data_scope)
    competitor_scope = data_scope if competitor_id is not None else None
    if competitor_scope is not None and canonical_province(province) not in competitor_scope.visible_provinces:
        raise HTTPException(status_code=403, detail="当前账号不能查看该区域的同行成交")
    orders = _signed_orders(db, province, competitor_id, year, competitor_scope)
    intentions = _province_intentions(db, province, competitor_scope)
    return DealHeatmapProvinceDetailRead(
        seller=seller,
        province=province,
        signed_amount=sum((order.amount for order in orders), start=Decimal(0)),
        signed_order_count=len(orders),
        orders=orders,
        intention_amount=sum((item.estimated_amount for item in intentions), start=Decimal(0)),
        intention_count=len(intentions),
        intentions=intentions,
    )
