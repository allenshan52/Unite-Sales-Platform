"""数据洞察聚合服务：从成交、单位地点和有效商机实时生成年度省市经营统计。"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import and_, extract, func, select
from sqlalchemy.orm import Session

from app.insights_schemas import (
    InsightsCustomerRead,
    InsightsKpisRead,
    InsightsMetric,
    InsightsMacroRegionRead,
    InsightsOverviewRead,
    InsightsPeriod,
    InsightsScopeMode,
    InsightsRegionRead,
    InsightsScopeRead,
    InsightsSignalRead,
    InsightsStageRead,
    InsightsTrendPointRead,
)
from app.models import Opportunity, OpportunityStage, Organization, OrganizationSite, SalesProject
from app.sales_coverage import SALES_PROVINCES, SALES_REGION_PROVINCES, canonical_province
from app.services.account_access import AccountDataScope, location_condition, province_storage_names
from app.services.deal_heatmap import active_opportunity_statement

ZERO = Decimal("0")
ONE_DECIMAL = Decimal("0.1")


def _period_bounds(year: int, period: InsightsPeriod) -> tuple[date, date]:
    """把全年或自然季度转换为左闭右开日期范围，避免月底边界误差。"""

    if period == InsightsPeriod.year:
        return date(year, 1, 1), date(year + 1, 1, 1)
    quarter = int(period.value[1])
    start_month = (quarter - 1) * 3 + 1
    end_year = year + (1 if quarter == 4 else 0)
    end_month = 1 if quarter == 4 else start_month + 3
    return date(year, start_month, 1), date(end_year, end_month, 1)


def _previous_quarter(year: int, period: InsightsPeriod) -> tuple[int, InsightsPeriod] | None:
    """返回季度环比基期；全年没有稳定的自然环比，明确返回空。"""

    if period == InsightsPeriod.year:
        return None
    quarter = int(period.value[1])
    return (year - 1, InsightsPeriod.q4) if quarter == 1 else (year, InsightsPeriod(f"q{quarter - 1}"))


def _percent(current: Decimal | int, previous: Decimal | int) -> Decimal | None:
    """安全计算一位小数变化率；基期为零时不伪造百分比。"""

    current_value = Decimal(current)
    previous_value = Decimal(previous)
    if previous_value == 0:
        return None
    return (((current_value - previous_value) / previous_value) * 100).quantize(ONE_DECIMAL, rounding=ROUND_HALF_UP)


def _sales_statement():
    """构造实际成交公共查询边界，统一排除归档单位与非正合同额。"""

    return (
        select(SalesProject, Organization.name, OrganizationSite)
        .join(Organization, Organization.id == SalesProject.organization_id)
        .join(
            OrganizationSite,
            and_(OrganizationSite.organization_id == Organization.id, OrganizationSite.is_primary.is_(True)),
        )
        .where(
            Organization.archived_at.is_(None),
            SalesProject.contract_amount > 0,
            SalesProject.signed_at.is_not(None),
        )
    )


def _scope_where(
    statement,
    province: str | None,
    city: str | None,
    data_scope: AccountDataScope,
):
    """把省市筛选应用到已连接主地点的查询，城市不能越过所属省份。"""

    statement = statement.where(location_condition(OrganizationSite.province, OrganizationSite.city, data_scope))
    if province:
        statement = statement.where(OrganizationSite.province.in_(province_storage_names(province)))
    if city:
        statement = statement.where(OrganizationSite.city == city)
    return statement


def _sales_summary(
    db: Session,
    year: int,
    period: InsightsPeriod,
    province: str | None,
    city: str | None,
    data_scope: AccountDataScope,
) -> tuple[Decimal, int]:
    """按时间与区域返回实际成交总额和项目数。"""

    start, end = _period_bounds(year, period)
    statement = _scope_where(_sales_statement(), province, city, data_scope).where(
        SalesProject.signed_at >= start,
        SalesProject.signed_at < end,
    ).with_only_columns(
        func.coalesce(func.sum(SalesProject.contract_amount), 0),
        func.count(SalesProject.id),
    )
    amount, count = db.execute(statement).one()
    return Decimal(amount), int(count)


def _pipeline_summary(
    db: Session,
    province: str | None,
    city: str | None,
    data_scope: AccountDataScope,
) -> tuple[Decimal, int]:
    """按区域聚合当前有效商机快照，不把预计金额混入实际销售。"""

    statement = _scope_where(active_opportunity_statement(), province, city, data_scope).with_only_columns(
        func.coalesce(func.sum(Opportunity.estimated_amount), 0),
        func.count(Opportunity.id),
    )
    amount, count = db.execute(statement).one()
    return Decimal(amount), int(count)


def _region_sales_map(
    db: Session,
    year: int,
    period: InsightsPeriod,
    province: str | None,
    data_scope: AccountDataScope,
) -> dict[str, tuple[Decimal, int]]:
    """单次聚合同层区域的基期销售，避免贡献榜逐区域发起比较查询。"""

    group_column = OrganizationSite.city if province else OrganizationSite.province
    start, end = _period_bounds(year, period)
    statement = (
        _scope_where(_sales_statement(), province, None, data_scope)
        .where(group_column.is_not(None), SalesProject.signed_at >= start, SalesProject.signed_at < end)
        .with_only_columns(
            group_column,
            func.coalesce(func.sum(SalesProject.contract_amount), 0),
            func.count(SalesProject.id),
        )
        .group_by(group_column)
    )
    return {str(name): (Decimal(amount), int(count)) for name, amount, count in db.execute(statement).all()}


def _region_rows(
    db: Session,
    year: int,
    period: InsightsPeriod,
    metric: InsightsMetric,
    province: str | None,
    city: str | None,
    data_scope: AccountDataScope,
) -> list[InsightsRegionRead]:
    """合并同层级成交与商机；全国视角只展示当前期间已有实际销售的省份。"""

    if city:
        return []
    group_column = OrganizationSite.city if province else OrganizationSite.province
    start, end = _period_bounds(year, period)
    sales_rows = db.execute(
        _scope_where(_sales_statement(), province, None, data_scope)
        .where(group_column.is_not(None), SalesProject.signed_at >= start, SalesProject.signed_at < end)
        .with_only_columns(
            group_column,
            func.coalesce(func.sum(SalesProject.contract_amount), 0),
            func.count(SalesProject.id),
            func.avg(OrganizationSite.longitude),
            func.avg(OrganizationSite.latitude),
        )
        .group_by(group_column)
    ).all()
    pipeline_rows = db.execute(
        _scope_where(active_opportunity_statement(), province, None, data_scope)
        .where(group_column.is_not(None))
        .with_only_columns(
            group_column,
            func.coalesce(func.sum(Opportunity.estimated_amount), 0),
            func.count(Opportunity.id),
            func.avg(OrganizationSite.longitude),
            func.avg(OrganizationSite.latitude),
        )
        .group_by(group_column)
    ).all()
    merged: dict[str, dict[str, object]] = {}
    for name, amount, count, longitude, latitude in sales_rows:
        merged[str(name)] = {
            "sales": Decimal(amount), "projects": int(count), "pipeline": ZERO, "pipeline_count": 0,
            "longitude": float(longitude) if longitude is not None else None,
            "latitude": float(latitude) if latitude is not None else None,
        }
    for name, amount, count, longitude, latitude in pipeline_rows:
        row = merged.setdefault(str(name), {"sales": ZERO, "projects": 0, "pipeline": ZERO, "pipeline_count": 0, "longitude": None, "latitude": None})
        row["pipeline"] = Decimal(amount)
        row["pipeline_count"] = int(count)
        row["longitude"] = row["longitude"] if row["longitude"] is not None else (float(longitude) if longitude is not None else None)
        row["latitude"] = row["latitude"] if row["latitude"] is not None else (float(latitude) if latitude is not None else None)

    if province is None:
        merged = {name: row for name, row in merged.items() if Decimal(row["sales"]) > ZERO}

    previous = _region_sales_map(db, year - 1, period, province, data_scope)
    previous_quarter = _previous_quarter(year, period)
    previous_quarter_values = _region_sales_map(db, previous_quarter[0], previous_quarter[1], province, data_scope) if previous_quarter else {}

    def selected_value(row: dict[str, object]) -> Decimal:
        if metric == InsightsMetric.projects:
            return Decimal(int(row["projects"]))
        if metric == InsightsMetric.pipeline:
            return Decimal(row["pipeline"])
        return Decimal(row["sales"])

    total = sum((selected_value(row) for row in merged.values()), start=ZERO)
    if province is None:
        province_order = {province_storage_names(name)[-1]: index for index, name in enumerate(SALES_PROVINCES)}
        ordered = sorted(merged.items(), key=lambda item: (province_order.get(item[0], len(province_order)), item[0]))
    else:
        ordered = sorted(merged.items(), key=lambda item: item[0])
    result: list[InsightsRegionRead] = []
    for rank, (name, row) in enumerate(ordered, start=1):
        sales = Decimal(row["sales"])
        projects = int(row["projects"])
        value = selected_value(row)
        previous_sales, previous_projects = previous.get(name, (ZERO, 0))
        comparison_current = Decimal(projects) if metric == InsightsMetric.projects else sales
        comparison_previous = Decimal(previous_projects) if metric == InsightsMetric.projects else previous_sales
        qoq = None
        if metric != InsightsMetric.pipeline and previous_quarter:
            previous_q_sales, previous_q_projects = previous_quarter_values.get(name, (ZERO, 0))
            qoq = _percent(comparison_current, Decimal(previous_q_projects) if metric == InsightsMetric.projects else previous_q_sales)
        result.append(InsightsRegionRead(
            id=name,
            name=name,
            province=province or name,
            city=name if province else None,
            longitude=row["longitude"],
            latitude=row["latitude"],
            sales_amount=sales,
            project_count=projects,
            pipeline_amount=Decimal(row["pipeline"]),
            pipeline_count=int(row["pipeline_count"]),
            average_deal_amount=(sales / projects).quantize(Decimal("0.01")) if projects else ZERO,
            metric_value=value,
            contribution_percent=((value / total) * 100).quantize(ONE_DECIMAL, rounding=ROUND_HALF_UP) if total else ZERO,
            rank=rank,
            yoy_percent=None if metric == InsightsMetric.pipeline else _percent(comparison_current, comparison_previous),
            qoq_percent=qoq,
        ))
    return result


def _trend(db: Session, year: int, province: str | None, city: str | None, data_scope: AccountDataScope) -> list[InsightsTrendPointRead]:
    """一次查询当前年与上一年成交，补齐没有成交的月份。"""

    statement = _scope_where(_sales_statement(), province, city, data_scope).where(
        SalesProject.signed_at >= date(year - 1, 1, 1),
        SalesProject.signed_at < date(year + 1, 1, 1),
    ).with_only_columns(
        extract("year", SalesProject.signed_at),
        extract("month", SalesProject.signed_at),
        func.coalesce(func.sum(SalesProject.contract_amount), 0),
    ).group_by(extract("year", SalesProject.signed_at), extract("month", SalesProject.signed_at))
    values = {(int(row_year), int(month)): Decimal(amount) for row_year, month, amount in db.execute(statement).all()}
    return [InsightsTrendPointRead(month=month, current_amount=values.get((year, month), ZERO), previous_amount=values.get((year - 1, month), ZERO)) for month in range(1, 13)]


def _top_customers(
    db: Session,
    year: int,
    period: InsightsPeriod,
    province: str | None,
    city: str | None,
    data_scope: AccountDataScope,
    limit: int = 10,
) -> list[InsightsCustomerRead]:
    """按单位聚合当前范围成交额，最多返回页面所需十项。"""

    start, end = _period_bounds(year, period)
    statement = _scope_where(_sales_statement(), province, city, data_scope).where(
        SalesProject.signed_at >= start,
        SalesProject.signed_at < end,
    ).with_only_columns(
        Organization.id,
        Organization.name,
        OrganizationSite.province,
        OrganizationSite.city,
        func.sum(SalesProject.contract_amount).label("sales_amount"),
        func.count(SalesProject.id),
        func.max(SalesProject.signed_at),
    ).group_by(Organization.id, Organization.name, OrganizationSite.province, OrganizationSite.city).order_by(
        func.sum(SalesProject.contract_amount).desc(), Organization.name,
    ).limit(limit)
    return [InsightsCustomerRead(
        rank=index,
        name=name,
        province=customer_province or "未填写",
        city=customer_city or "未填写",
        sales_amount=Decimal(amount),
        project_count=int(count),
        latest_signed_at=latest,
    ) for index, (_id, name, customer_province, customer_city, amount, count, latest) in enumerate(db.execute(statement).all(), start=1)]


def _stages(db: Session, province: str | None, city: str | None, data_scope: AccountDataScope) -> list[InsightsStageRead]:
    """按业务推进顺序汇总当前有效商机阶段，金额占比用于抽屉堆叠条。"""

    statement = _scope_where(active_opportunity_statement(), province, city, data_scope).with_only_columns(
        Opportunity.stage,
        func.count(Opportunity.id),
        func.coalesce(func.sum(Opportunity.estimated_amount), 0),
    ).group_by(Opportunity.stage)
    rows = {stage: (int(count), Decimal(amount)) for stage, count, amount in db.execute(statement).all()}
    order = [OpportunityStage.identified, OpportunityStage.qualifying, OpportunityStage.proposal, OpportunityStage.negotiation]
    total = sum((rows.get(stage, (0, ZERO))[1] for stage in order), start=ZERO)
    return [InsightsStageRead(
        stage=stage.value,
        opportunity_count=rows.get(stage, (0, ZERO))[0],
        amount=rows.get(stage, (0, ZERO))[1],
        percent=((rows.get(stage, (0, ZERO))[1] / total) * 100).quantize(ONE_DECIMAL, rounding=ROUND_HALF_UP) if total else ZERO,
    ) for stage in order]


def _signals(regions: list[InsightsRegionRead], kpis: InsightsKpisRead, period: InsightsPeriod) -> list[InsightsSignalRead]:
    """从当前响应计算最多三条可解释提示，数据不足时明确说明而不编造。"""

    if not regions:
        return [InsightsSignalRead(tone="neutral", title="当前期间暂无成交", description="可切换年份或季度查看历史经营数据。")]
    top = max(regions, key=lambda item: item.sales_amount)
    pipeline = max(regions, key=lambda item: item.pipeline_amount)
    total_sales = sum((item.sales_amount for item in regions), start=ZERO)
    top_sales_share = ((top.sales_amount / total_sales) * 100).quantize(ONE_DECIMAL) if total_sales else ZERO
    signals = [InsightsSignalRead(
        tone="positive",
        title=f"{top.name}成交贡献居首",
        description=f"实际销售额占当前区域合计 {top_sales_share}%。",
    )]
    if pipeline.pipeline_amount > 0:
        ratio = ((pipeline.pipeline_amount / pipeline.sales_amount) * 100).quantize(ONE_DECIMAL) if pipeline.sales_amount else None
        description = f"有效商机储备为实际销售的 {ratio}%。" if ratio is not None else "当前有有效商机储备，但本期间尚无实际成交。"
        signals.append(InsightsSignalRead(tone="warning", title=f"{pipeline.name}商机储备最高", description=description))
    comparison = kpis.sales_qoq_percent if period != InsightsPeriod.year else kpis.sales_yoy_percent
    label = "环比" if period != InsightsPeriod.year else "同比"
    signals.append(InsightsSignalRead(
        tone="positive" if comparison is not None and comparison >= 0 else "neutral",
        title=f"整体销售{label}{'增长' if comparison is not None and comparison >= 0 else '变化'}",
        description=f"当前口径较基期 {comparison:+.1f}%。" if comparison is not None else "基期没有成交，暂不计算变化率。",
    ))
    return signals[:3]


def _macro_regions(
    regions: list[InsightsRegionRead],
    metric: InsightsMetric,
    data_scope: AccountDataScope,
) -> list[InsightsMacroRegionRead]:
    """把省级结果按七个固定大区聚合，同一大区内省份共享热力值。"""

    visible_regions = set(SALES_REGION_PROVINCES) if data_scope.unrestricted else set(data_scope.regions)
    grouped: list[tuple[str, Decimal, int, Decimal, int]] = []
    for region_name, provinces in SALES_REGION_PROVINCES.items():
        if region_name not in visible_regions:
            continue
        rows = [row for row in regions if canonical_province(row.province) in provinces]
        grouped.append((
            region_name,
            sum((row.sales_amount for row in rows), start=ZERO),
            sum(row.project_count for row in rows),
            sum((row.pipeline_amount for row in rows), start=ZERO),
            sum(row.pipeline_count for row in rows),
        ))
    values = [Decimal(projects) if metric == InsightsMetric.projects else pipeline if metric == InsightsMetric.pipeline else sales for _name, sales, projects, pipeline, _count in grouped]
    total = sum(values, start=ZERO)
    return [InsightsMacroRegionRead(
        id=name,
        name=name,
        provinces=[province_storage_names(province)[-1] for province in SALES_REGION_PROVINCES[name]],
        sales_amount=sales,
        project_count=projects,
        pipeline_amount=pipeline,
        pipeline_count=pipeline_count,
        metric_value=value,
        contribution_percent=((value / total) * 100).quantize(ONE_DECIMAL, rounding=ROUND_HALF_UP) if total else ZERO,
    ) for (name, sales, projects, pipeline, pipeline_count), value in zip(grouped, values, strict=True)]


def get_insights_overview(
    db: Session,
    year: int,
    period: InsightsPeriod,
    metric: InsightsMetric,
    data_scope: AccountDataScope,
    scope_mode: InsightsScopeMode = InsightsScopeMode.assigned,
    province: str | None = None,
    city: str | None = None,
) -> InsightsOverviewRead:
    """生成数据洞察页面或城市抽屉所需的单一、同口径聚合响应。"""

    sales_amount, project_count = _sales_summary(db, year, period, province, city, data_scope)
    previous_amount, previous_count = _sales_summary(db, year - 1, period, province, city, data_scope)
    previous_quarter = _previous_quarter(year, period)
    previous_q_amount, previous_q_count = _sales_summary(db, previous_quarter[0], previous_quarter[1], province, city, data_scope) if previous_quarter else (ZERO, 0)
    pipeline_amount, pipeline_count = _pipeline_summary(db, province, city, data_scope)
    regions = _region_rows(db, year, period, metric, province, city, data_scope)
    years = [int(value) for value in db.execute(
        _scope_where(_sales_statement(), None, None, data_scope)
        .with_only_columns(extract("year", SalesProject.signed_at))
        .distinct()
        .order_by(extract("year", SalesProject.signed_at).desc())
    ).scalars().all()]
    if year not in years:
        years.append(year)
        years.sort(reverse=True)
    kpis = InsightsKpisRead(
        sales_amount=sales_amount,
        sales_yoy_percent=_percent(sales_amount, previous_amount),
        sales_qoq_percent=_percent(sales_amount, previous_q_amount) if previous_quarter else None,
        project_count=project_count,
        projects_yoy_percent=_percent(project_count, previous_count),
        projects_qoq_percent=_percent(project_count, previous_q_count) if previous_quarter else None,
        average_deal_amount=(sales_amount / project_count).quantize(Decimal("0.01")) if project_count else ZERO,
        pipeline_amount=pipeline_amount,
        pipeline_count=pipeline_count,
        active_region_count=sum(row.sales_amount > 0 or row.pipeline_amount > 0 for row in regions) if not city else int(sales_amount > 0 or pipeline_amount > 0),
    )
    scope = InsightsScopeRead(
        level="city" if city else "province" if province else "national",
        name=city or province or "全国",
        province=province,
        city=city,
        mode=scope_mode,
        visible_provinces=[province_storage_names(item)[-1] for item in SALES_PROVINCES if item in data_scope.visible_provinces],
        visible_regions=[item for item in SALES_REGION_PROVINCES if data_scope.unrestricted or item in data_scope.regions],
    )
    return InsightsOverviewRead(
        year=year,
        period=period,
        metric=metric,
        available_years=years,
        scope=scope,
        aggregated_at=datetime.now(UTC),
        kpis=kpis,
        regions=regions,
        macro_regions=_macro_regions(regions, metric, data_scope) if province is None and scope_mode == InsightsScopeMode.region else [],
        trend=_trend(db, year, province, city, data_scope),
        signals=_signals(regions, kpis, period),
        top_customers=_top_customers(db, year, period, province, city, data_scope),
        stages=_stages(db, province, city, data_scope),
    )
