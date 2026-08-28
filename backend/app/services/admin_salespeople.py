"""销售人员聚合管理服务：在单一事务中维护主档、分级覆盖范围和活动流水。"""

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.admin_data_schemas import (
    SalesActivityProfileRead,
    SalespersonCoverageScopeProfileRead,
    SalespersonAdminListItem,
    SalespersonAdminListPage,
    SalespersonProfileInput,
    SalespersonProfileRead,
)
from app.models import AuditLog, SalesActivity, SalesActivityType, Salesperson, SalespersonCoverageScope, SalesProject
from app.services.salespeople import month_cutoff


def list_salesperson_profiles(
    db: Session,
    *,
    page: int,
    page_size: int,
    search: str | None,
    now: datetime | None = None,
) -> SalespersonAdminListPage:
    """分页读取销售主档，并批量聚合前十个覆盖范围、实际成交额和近三个月活动。"""

    conditions = []
    if search and search.strip():
        keyword = f"%{search.strip()}%"
        conditions.append(or_(Salesperson.display_name.ilike(keyword), Salesperson.employee_code.ilike(keyword)))
    total = db.scalar(select(func.count(Salesperson.id)).where(*conditions)) or 0
    salespeople = list(db.scalars(
        select(Salesperson)
        .where(*conditions)
        .order_by(Salesperson.employee_code, Salesperson.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all())
    salesperson_ids = [item.id for item in salespeople]
    if not salesperson_ids:
        return SalespersonAdminListPage(items=[], total=total, page=page, page_size=page_size)

    coverage_names: dict[UUID, list[str]] = defaultdict(list)
    for salesperson_id, scope_level, scope_name in db.execute(
        select(SalespersonCoverageScope.salesperson_id, SalespersonCoverageScope.scope_level, SalespersonCoverageScope.scope_name)
        .where(SalespersonCoverageScope.salesperson_id.in_(salesperson_ids))
        .order_by(SalespersonCoverageScope.salesperson_id, SalespersonCoverageScope.scope_level, SalespersonCoverageScope.scope_name)
    ):
        coverage_names[salesperson_id].append(scope_name if scope_name == "全国" else f"{scope_name}（{scope_level.value}）")

    activity_counts: dict[UUID, dict[SalesActivityType, int]] = defaultdict(dict)
    for salesperson_id, activity_type, count in db.execute(
        select(SalesActivity.salesperson_id, SalesActivity.activity_type, func.count(SalesActivity.id))
        .where(SalesActivity.salesperson_id.in_(salesperson_ids), SalesActivity.occurred_at >= month_cutoff(now or datetime.now(UTC), 3))
        .group_by(SalesActivity.salesperson_id, SalesActivity.activity_type)
    ):
        activity_counts[salesperson_id][activity_type] = count

    project_totals = {
        salesperson_id: amount or Decimal(0)
        for salesperson_id, amount in db.execute(
            select(SalesProject.salesperson_id, func.sum(SalesProject.contract_amount))
            .where(SalesProject.salesperson_id.in_(salesperson_ids))
            .group_by(SalesProject.salesperson_id)
        )
    }
    items = []
    for salesperson in salespeople:
        counts = activity_counts[salesperson.id]
        scopes = coverage_names[salesperson.id]
        items.append(SalespersonAdminListItem(
            id=salesperson.id,
            employee_code=salesperson.employee_code,
            display_name=salesperson.display_name,
            color=salesperson.color,
            coverage_scopes=scopes[:10],
            coverage_scope_total=len(scopes),
            actual_sales_amount=project_totals.get(salesperson.id, Decimal(0)),
            visit_count=counts.get(SalesActivityType.visit, 0),
            demonstration_count=counts.get(SalesActivityType.demonstration, 0),
            marketing_event_count=counts.get(SalesActivityType.marketing_event, 0),
            is_active=salesperson.is_active,
        ))
    return SalespersonAdminListPage(items=items, total=total, page=page, page_size=page_size)


def _profile_statement() -> Any:
    """集中声明完整档案预加载，避免序列化阶段逐条触发数据库查询。"""

    return select(Salesperson).options(
        selectinload(Salesperson.coverage_scopes),
        selectinload(Salesperson.activities).selectinload(SalesActivity.organization),
    )


def get_salesperson_profile(db: Session, salesperson_id: UUID) -> Salesperson:
    """读取一名销售及全部内嵌记录，不存在时返回中文 404。"""

    salesperson = db.scalar(_profile_statement().where(Salesperson.id == salesperson_id))
    if salesperson is None:
        raise HTTPException(status_code=404, detail="未找到该销售人员")
    return salesperson


def to_profile_read(salesperson: Salesperson) -> SalespersonProfileRead:
    """把预加载的 ORM 档案转换为稳定、排序明确的管理端响应。"""

    coverage_scopes = sorted(salesperson.coverage_scopes, key=lambda item: (item.scope_level.value, item.scope_name, str(item.id)))
    activities = sorted(salesperson.activities, key=lambda item: (item.occurred_at, str(item.id)), reverse=True)
    return SalespersonProfileRead(
        id=salesperson.id,
        employee_code=salesperson.employee_code,
        display_name=salesperson.display_name,
        color=salesperson.color,
        coverage_center_longitude=salesperson.coverage_center_longitude,
        coverage_center_latitude=salesperson.coverage_center_latitude,
        is_active=salesperson.is_active,
        coverage_scopes=[
            SalespersonCoverageScopeProfileRead(
                id=item.id,
                scope_level=item.scope_level,
                scope_name=item.scope_name,
                province=item.province,
                city=item.city,
                amap_adcode=item.amap_adcode,
            )
            for item in coverage_scopes
        ],
        activities=[
            SalesActivityProfileRead(
                id=item.id,
                organization_id=item.organization_id,
                organization_name=item.organization.name if item.organization is not None else None,
                activity_type=item.activity_type,
                occurred_at=item.occurred_at,
                province=item.province,
                city=item.city,
                amap_adcode=item.amap_adcode,
                notes=item.notes,
            )
            for item in activities
        ],
        created_at=salesperson.created_at,
        updated_at=salesperson.updated_at,
    )


def _commit_profile(db: Session) -> None:
    """提交聚合写入，并把数据库约束转换为不泄露 SQL 的中文错误。"""

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="员工编号或覆盖范围与现有数据重复，或该销售仍被其他业务记录引用") from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="销售人员档案保存失败，请稍后重试") from error


def _sync_children(db: Session, records: list[Any], payloads: list[Any], model_class: type[Any], label: str) -> None:
    """按子记录 ID 更新、新增并删除集合，同时拒绝借用其他销售的记录 ID。"""

    existing = {record.id: record for record in records}
    retained_ids: set[UUID] = set()
    for payload in payloads:
        values = payload.model_dump(exclude={"id"})
        if payload.id is None:
            records.append(model_class(id=uuid4(), **values))
            continue
        record = existing.get(payload.id)
        if record is None:
            raise HTTPException(status_code=422, detail=f"{label}记录不属于当前销售人员")
        retained_ids.add(payload.id)
        for field_name, value in values.items():
            setattr(record, field_name, value)
    for record_id, record in existing.items():
        if record_id not in retained_ids:
            db.delete(record)


def create_salesperson_profile(db: Session, payload: SalespersonProfileInput, actor_username: str) -> SalespersonProfileRead:
    """原子新增销售主档及全部覆盖、活动记录，并写入管理员审计。"""

    base_values = payload.model_dump(exclude={"coverage_scopes", "activities"})
    salesperson = Salesperson(
        id=uuid4(),
        **base_values,
        coverage_scopes=[
            SalespersonCoverageScope(id=uuid4(), **item.model_dump(exclude={"id"}))
            for item in payload.coverage_scopes
        ],
        activities=[SalesActivity(id=uuid4(), **item.model_dump(exclude={"id"})) for item in payload.activities],
    )
    db.add(salesperson)
    db.add(AuditLog(
        organization_id=None,
        actor_username=actor_username,
        action="新增销售人员档案",
        detail={"销售人员ID": str(salesperson.id), "覆盖范围数量": len(payload.coverage_scopes), "活动数量": len(payload.activities)},
    ))
    _commit_profile(db)
    return to_profile_read(get_salesperson_profile(db, salesperson.id))


def update_salesperson_profile(
    db: Session,
    salesperson_id: UUID,
    payload: SalespersonProfileInput,
    actor_username: str,
) -> SalespersonProfileRead:
    """原子覆盖销售主档并同步两个子集合，失败时整笔事务回滚。"""

    salesperson = get_salesperson_profile(db, salesperson_id)
    for field_name, value in payload.model_dump(exclude={"coverage_scopes", "activities"}).items():
        setattr(salesperson, field_name, value)
    _sync_children(db, salesperson.coverage_scopes, payload.coverage_scopes, SalespersonCoverageScope, "覆盖范围")
    _sync_children(db, salesperson.activities, payload.activities, SalesActivity, "销售活动")
    db.add(AuditLog(
        organization_id=None,
        actor_username=actor_username,
        action="编辑销售人员档案",
        detail={"销售人员ID": str(salesperson.id), "覆盖范围数量": len(payload.coverage_scopes), "活动数量": len(payload.activities)},
    ))
    _commit_profile(db)
    return to_profile_read(get_salesperson_profile(db, salesperson_id))


def delete_salesperson_profile(db: Session, salesperson_id: UUID, actor_username: str) -> None:
    """删除销售及其内嵌覆盖、活动；其他业务引用仍由数据库阻止并完整回滚。"""

    salesperson = db.get(Salesperson, salesperson_id)
    if salesperson is None:
        raise HTTPException(status_code=404, detail="未找到该销售人员")
    db.execute(delete(SalesActivity).where(SalesActivity.salesperson_id == salesperson_id))
    db.execute(delete(SalespersonCoverageScope).where(SalespersonCoverageScope.salesperson_id == salesperson_id))
    db.delete(salesperson)
    db.add(AuditLog(
        organization_id=None,
        actor_username=actor_username,
        action="删除销售人员档案",
        detail={"销售人员ID": str(salesperson_id), "员工编号": salesperson.employee_code},
    ))
    _commit_profile(db)
