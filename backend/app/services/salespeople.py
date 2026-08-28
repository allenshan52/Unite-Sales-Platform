"""销售覆盖公开查询服务：按统一滚动月份聚合活动、成交和储备金额。"""

from calendar import monthrange
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Opportunity,
    OpportunityStage,
    SalesActivity,
    SalesActivityType,
    Salesperson,
    SalesProject,
)
from app.schemas import (
    SalespersonActivitySummaryRead,
    SalespersonCoverageScopeRead,
    SalespersonCoverageRead,
    SalespersonPerformanceRead,
)
from app.sales_coverage import included_provinces


def month_cutoff(now: datetime, months: int) -> datetime:
    """按自然月回退并夹紧月末，确保 1/3/6/12 月窗口不漂移为固定天数。"""

    month_index = now.year * 12 + now.month - 1 - months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    return now.replace(year=year, month=month, day=min(now.day, monthrange(year, month)[1]))


def list_public_salesperson_coverage(
    db: Session,
    months: int,
    *,
    salesperson_id: UUID | None = None,
    now: datetime | None = None,
) -> list[SalespersonCoverageRead]:
    """一次返回授权销售和所选期间汇总；个人账号查询固定到关联销售 ID。"""

    cutoff = month_cutoff(now or datetime.now(UTC), months)
    salesperson_statement = (
        select(Salesperson)
        .options(selectinload(Salesperson.coverage_scopes))
        .where(Salesperson.is_active.is_(True))
        .order_by(Salesperson.employee_code)
    )
    if salesperson_id is not None:
        salesperson_statement = salesperson_statement.where(Salesperson.id == salesperson_id)
    salespeople = db.scalars(salesperson_statement).all()

    activity_counts: dict[object, dict[SalesActivityType, int]] = defaultdict(dict)
    for salesperson_id, activity_type, count in db.execute(
        select(SalesActivity.salesperson_id, SalesActivity.activity_type, func.count(SalesActivity.id))
        .where(SalesActivity.occurred_at >= cutoff)
        .group_by(SalesActivity.salesperson_id, SalesActivity.activity_type)
    ):
        activity_counts[salesperson_id][activity_type] = count

    project_totals = {
        salesperson_id: (count, amount or Decimal(0))
        for salesperson_id, count, amount in db.execute(
            select(SalesProject.salesperson_id, func.count(SalesProject.id), func.sum(SalesProject.contract_amount))
            .where(SalesProject.salesperson_id.is_not(None))
            .group_by(SalesProject.salesperson_id)
        )
    }
    pipeline_totals = {
        salesperson_id: (count, amount or Decimal(0))
        for salesperson_id, count, amount in db.execute(
            select(Opportunity.salesperson_id, func.count(Opportunity.id), func.sum(Opportunity.estimated_amount))
            .where(
                Opportunity.salesperson_id.is_not(None),
                Opportunity.stage != OpportunityStage.closed_lost,
            )
            .group_by(Opportunity.salesperson_id)
        )
    }

    result: list[SalespersonCoverageRead] = []
    for salesperson in salespeople:
        counts = activity_counts[salesperson.id]
        visits = counts.get(SalesActivityType.visit, 0)
        demonstrations = counts.get(SalesActivityType.demonstration, 0)
        marketing_events = counts.get(SalesActivityType.marketing_event, 0)
        project_count, actual_sales_amount = project_totals.get(salesperson.id, (0, Decimal(0)))
        opportunity_count, pipeline_amount = pipeline_totals.get(salesperson.id, (0, Decimal(0)))
        result.append(SalespersonCoverageRead(
            id=salesperson.id,
            employee_code=salesperson.employee_code,
            display_name=salesperson.display_name,
            color=salesperson.color,
            coverage_center_longitude=salesperson.coverage_center_longitude,
            coverage_center_latitude=salesperson.coverage_center_latitude,
            coverage_scopes=[
                SalespersonCoverageScopeRead(
                    scope_level=scope.scope_level.value,
                    scope_name=scope.scope_name,
                    province=scope.province,
                    city=scope.city,
                    amap_adcode=scope.amap_adcode,
                    included_provinces=included_provinces(scope.scope_level, scope.scope_name, scope.province),
                )
                for scope in sorted(salesperson.coverage_scopes, key=lambda item: (item.scope_level.value, item.scope_name))
            ],
            performance=SalespersonPerformanceRead(
                period_months=months,
                activities=SalespersonActivitySummaryRead(
                    visits=visits,
                    demonstrations=demonstrations,
                    marketing_events=marketing_events,
                    total=visits + demonstrations + marketing_events,
                ),
                actual_sales_amount=actual_sales_amount,
                pipeline_amount=pipeline_amount,
                project_count=project_count,
                active_opportunity_count=opportunity_count,
            ),
        ))
    return result
