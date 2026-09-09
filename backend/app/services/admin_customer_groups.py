"""客户集团聚合管理服务：分页汇总主档，并在单一事务中同步完整单位树。"""

from collections import defaultdict, deque
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from geoalchemy2.elements import WKTElement
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.admin_data_schemas import (
    CustomerGroupAdminListItem,
    CustomerGroupAdminListPage,
    CustomerGroupProfileInput,
    CustomerGroupProfileRead,
    CustomerGroupUnitProfileInput,
    CustomerGroupUnitProfileRead,
)
from app.models import AuditLog, CustomerGroup, CustomerGroupUnit, OpportunityStage
from app.services.account_access import AccountDataScope, customer_group_visibility_condition
from app.services.geocoding import gcj02_to_wgs84


def list_customer_group_profiles(
    db: Session,
    *,
    page: int,
    page_size: int,
    search: str | None,
    data_scope: AccountDataScope | None = None,
) -> CustomerGroupAdminListPage:
    """分页读取账号范围内集团，并用固定批量查询聚合总部、分支、成交和商机。"""

    conditions = []
    if data_scope is not None:
        conditions.append(customer_group_visibility_condition(data_scope))
    if search and search.strip():
        conditions.append(CustomerGroup.name.ilike(f"%{search.strip()}%"))
    total = db.scalar(select(func.count(CustomerGroup.id)).where(*conditions)) or 0
    groups = list(db.scalars(
        select(CustomerGroup)
        .where(*conditions)
        .order_by(CustomerGroup.name, CustomerGroup.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all())
    group_ids = [group.id for group in groups]
    if not group_ids:
        return CustomerGroupAdminListPage(items=[], total=total, page=page, page_size=page_size)

    headquarters = {
        group_id: (name, city)
        for group_id, name, city in db.execute(
            select(CustomerGroupUnit.group_id, CustomerGroupUnit.name, CustomerGroupUnit.city)
            .where(CustomerGroupUnit.group_id.in_(group_ids), CustomerGroupUnit.is_headquarters.is_(True))
        )
    }
    aggregates = {
        group_id: (branch_count, won_count, active_count, actual_amount, estimated_amount)
        for group_id, branch_count, won_count, active_count, actual_amount, estimated_amount in db.execute(
            select(
                CustomerGroupUnit.group_id,
                func.sum(case((CustomerGroupUnit.is_headquarters.is_(False), 1), else_=0)),
                func.sum(case((CustomerGroupUnit.is_won.is_(True), 1), else_=0)),
                func.sum(case((and_(
                    CustomerGroupUnit.opportunity_stage.is_not(None),
                    CustomerGroupUnit.opportunity_stage != OpportunityStage.closed_lost,
                ), 1), else_=0)),
                func.coalesce(func.sum(CustomerGroupUnit.actual_sales_amount), 0),
                func.coalesce(func.sum(CustomerGroupUnit.estimated_opportunity_amount), 0),
            )
            .where(CustomerGroupUnit.group_id.in_(group_ids))
            .group_by(CustomerGroupUnit.group_id)
        )
    }
    items = []
    for group in groups:
        headquarters_name, headquarters_city = headquarters.get(group.id, (None, None))
        branch_count, won_count, active_count, actual_amount, estimated_amount = aggregates.get(
            group.id, (0, 0, 0, Decimal(0), Decimal(0)),
        )
        items.append(CustomerGroupAdminListItem(
            id=group.id,
            name=group.name,
            color=group.color,
            headquarters_name=headquarters_name,
            headquarters_city=headquarters_city,
            branch_count=branch_count or 0,
            won_unit_count=won_count or 0,
            active_opportunity_count=active_count or 0,
            actual_sales_amount=actual_amount or Decimal(0),
            estimated_opportunity_amount=estimated_amount or Decimal(0),
        ))
    return CustomerGroupAdminListPage(items=items, total=total, page=page, page_size=page_size)


def _profile_statement() -> Any:
    """集中声明完整单位树预加载，避免档案序列化阶段产生逐节点查询。"""

    return select(CustomerGroup).options(selectinload(CustomerGroup.units))


def get_customer_group_profile(db: Session, group_id: UUID) -> CustomerGroup:
    """按集团 ID 读取主档及全部单位，不存在时返回统一中文 404。"""

    group = db.scalar(_profile_statement().where(CustomerGroup.id == group_id))
    if group is None:
        raise HTTPException(status_code=404, detail="未找到该客户集团")
    return group


def _ordered_units(units: list[CustomerGroupUnit]) -> list[CustomerGroupUnit]:
    """把有效单位树排成总部优先的层级顺序，并兼容待修复的历史孤立记录。"""

    headquarters = next((unit for unit in units if unit.is_headquarters), None)
    if headquarters is None:
        return sorted(units, key=lambda item: (item.name, str(item.id)))
    children: dict[UUID, list[CustomerGroupUnit]] = defaultdict(list)
    for unit in units:
        if unit.parent_id is not None:
            children[unit.parent_id].append(unit)
    for records in children.values():
        records.sort(key=lambda item: (item.name, str(item.id)))
    ordered: list[CustomerGroupUnit] = []
    seen: set[UUID] = set()
    pending: deque[CustomerGroupUnit] = deque([headquarters])
    while pending:
        unit = pending.popleft()
        if unit.id in seen:
            continue
        seen.add(unit.id)
        ordered.append(unit)
        pending.extend(children.get(unit.id, []))
    ordered.extend(sorted((unit for unit in units if unit.id not in seen), key=lambda item: (item.name, str(item.id))))
    return ordered


def to_profile_read(group: CustomerGroup) -> CustomerGroupProfileRead:
    """把 ORM 集团转换为稳定 DTO，并以数据库 UUID 作为编辑时的父子草稿键。"""

    return CustomerGroupProfileRead(
        id=group.id,
        name=group.name,
        color=group.color,
        units=[
            CustomerGroupUnitProfileRead(
                id=unit.id,
                draft_key=str(unit.id),
                parent_draft_key=str(unit.parent_id) if unit.parent_id else None,
                name=unit.name,
                is_headquarters=unit.is_headquarters,
                address=unit.address,
                province=unit.province,
                city=unit.city,
                longitude=unit.longitude,
                latitude=unit.latitude,
                is_won=unit.is_won,
                actual_sales_amount=unit.actual_sales_amount,
                opportunity_stage=unit.opportunity_stage,
                estimated_opportunity_amount=unit.estimated_opportunity_amount,
                created_at=unit.created_at,
                updated_at=unit.updated_at,
            )
            for unit in _ordered_units(group.units)
        ],
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


def _unit_values(payload: CustomerGroupUnitProfileInput) -> dict[str, Any]:
    """提取单位业务字段并同步派生 WGS84 空间点，保持地图数据口径不变。"""

    values = payload.model_dump(exclude={"id", "draft_key", "parent_draft_key"})
    longitude, latitude = gcj02_to_wgs84(payload.longitude, payload.latitude)
    values["location"] = WKTElement(f"POINT({longitude} {latitude})", srid=4326)
    return values


def _commit_profile(db: Session) -> None:
    """提交聚合写入，并把数据库约束转换为不泄露 SQL 的中文错误。"""

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="集团名称或单位名称与现有数据重复，请核对总部、层级和金额后重试") from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="客户集团档案保存失败，请稍后重试") from error


def create_customer_group_profile(
    db: Session,
    payload: CustomerGroupProfileInput,
    actor_username: str,
) -> CustomerGroupProfileRead:
    """原子新增集团主档与完整单位树，并写入管理员审计记录。"""

    if any(unit.id is not None for unit in payload.units):
        raise HTTPException(status_code=422, detail="新增集团的单位不能携带已有记录 ID")
    group = CustomerGroup(id=uuid4(), name=payload.name, color=payload.color)
    id_by_key = {unit.draft_key: uuid4() for unit in payload.units}
    group.units = [
        CustomerGroupUnit(
            id=id_by_key[unit.draft_key],
            parent_id=id_by_key.get(unit.parent_draft_key) if unit.parent_draft_key else None,
            **_unit_values(unit),
        )
        for unit in payload.units
    ]
    db.add(group)
    db.add(AuditLog(
        organization_id=None,
        actor_username=actor_username,
        action="新增客户集团档案",
        detail={"客户集团ID": str(group.id), "单位数量": len(payload.units)},
    ))
    _commit_profile(db)
    return to_profile_read(get_customer_group_profile(db, group.id))


def update_customer_group_profile(
    db: Session,
    group_id: UUID,
    payload: CustomerGroupProfileInput,
    actor_username: str,
) -> CustomerGroupProfileRead:
    """原子覆盖集团主档并同步单位树，拒绝借用其他集团的记录 ID。"""

    group = get_customer_group_profile(db, group_id)
    existing = {unit.id: unit for unit in group.units}
    current_headquarters = next((unit for unit in group.units if unit.is_headquarters), None)
    incoming_headquarters = next(unit for unit in payload.units if unit.is_headquarters)
    if current_headquarters is not None and incoming_headquarters.id != current_headquarters.id:
        raise HTTPException(status_code=422, detail="集团总部记录不能替换；可直接修改总部的全部业务字段")

    id_by_key: dict[str, UUID] = {}
    for item in payload.units:
        if item.id is not None and item.id not in existing:
            raise HTTPException(status_code=422, detail=f"单位“{item.name}”不属于当前客户集团")
        id_by_key[item.draft_key] = item.id or uuid4()

    retained_ids: set[UUID] = set()
    for item in payload.units:
        unit_id = id_by_key[item.draft_key]
        values = _unit_values(item)
        values["parent_id"] = id_by_key.get(item.parent_draft_key) if item.parent_draft_key else None
        if item.id is None:
            group.units.append(CustomerGroupUnit(id=unit_id, **values))
            continue
        retained_ids.add(item.id)
        record = existing[item.id]
        for field_name, value in values.items():
            setattr(record, field_name, value)

    group.name = payload.name
    group.color = payload.color
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="集团单位名称、总部或层级与现有数据冲突，请核对后重试") from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="客户集团档案保存失败，请稍后重试") from error
    for unit_id, record in existing.items():
        if unit_id not in retained_ids:
            db.delete(record)
    db.add(AuditLog(
        organization_id=None,
        actor_username=actor_username,
        action="更新客户集团档案",
        detail={"客户集团ID": str(group.id), "单位数量": len(payload.units)},
    ))
    _commit_profile(db)
    return to_profile_read(get_customer_group_profile(db, group.id))


def delete_customer_group_profile(db: Session, group_id: UUID, actor_username: str) -> None:
    """删除集团及其完整单位树，并通过数据库级联维持引用完整性。"""

    group = get_customer_group_profile(db, group_id)
    unit_count = len(group.units)
    group_name = group.name
    db.delete(group)
    db.add(AuditLog(
        organization_id=None,
        actor_username=actor_username,
        action="删除客户集团档案",
        detail={"客户集团ID": str(group_id), "集团名称": group_name, "单位数量": unit_count},
    ))
    _commit_profile(db)
