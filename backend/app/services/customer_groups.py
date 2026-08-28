"""客户集团公开查询服务：延迟加载关系树，并从单位记录计算销售汇总。"""

from collections import defaultdict, deque
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, exists, select
from sqlalchemy.orm import Session, selectinload

from app.models import CustomerGroup, CustomerGroupUnit, OpportunityStage
from app.schemas import (
    CustomerGroupDetailRead,
    CustomerGroupHeadquartersRead,
    CustomerGroupSummaryRead,
    CustomerGroupUnitRead,
)
from app.services.account_access import AccountDataScope, location_condition, location_is_visible


def _to_public_unit(unit: CustomerGroupUnit, level: int) -> CustomerGroupUnitRead:
    """把数据库单位转换为公开节点，显式排除联系人或内部备注等敏感字段。"""

    return CustomerGroupUnitRead(
        id=unit.id, parent_id=unit.parent_id, name=unit.name, level=level,
        is_headquarters=unit.is_headquarters, address=unit.address, province=unit.province,
        city=unit.city, longitude=unit.longitude, latitude=unit.latitude, is_won=unit.is_won,
        actual_sales_amount=unit.actual_sales_amount, opportunity_stage=unit.opportunity_stage,
        estimated_opportunity_amount=unit.estimated_opportunity_amount,
    )


def list_public_customer_group_headquarters(
    db: Session,
    data_scope: AccountDataScope | None = None,
) -> list[CustomerGroupHeadquartersRead]:
    """只查询账号范围内集团总部，控制首页默认地图载荷和区域边界。"""

    if data_scope is None:
        data_scope = AccountDataScope(True, frozenset(), frozenset(), frozenset())

    statement = (
        select(CustomerGroup, CustomerGroupUnit)
        .join(CustomerGroupUnit, and_(CustomerGroupUnit.group_id == CustomerGroup.id, CustomerGroupUnit.is_headquarters.is_(True)))
        .where(location_condition(CustomerGroupUnit.province, CustomerGroupUnit.city, data_scope))
        .order_by(CustomerGroup.name)
    )
    return [
        CustomerGroupHeadquartersRead(id=group.id, name=group.name, color=group.color, headquarters=_to_public_unit(headquarters, 0))
        for group, headquarters in db.execute(statement).all()
    ]


def _visible_group_units(group: CustomerGroup, data_scope: AccountDataScope) -> list[CustomerGroupUnit]:
    """保留范围内集团节点及其连接到总部所需祖先，避免关系树断裂或全国展开。"""

    if data_scope.unrestricted:
        return list(group.units)
    units_by_id = {unit.id: unit for unit in group.units}
    visible_ids = {
        unit.id for unit in group.units
        if location_is_visible(data_scope, unit.province, unit.city)
    }
    for unit_id in tuple(visible_ids):
        parent_id = units_by_id[unit_id].parent_id
        while parent_id is not None and parent_id not in visible_ids:
            visible_ids.add(parent_id)
            parent_id = units_by_id[parent_id].parent_id
    return [unit for unit in group.units if unit.id in visible_ids]


def build_public_customer_group_detail(
    group: CustomerGroup,
    data_scope: AccountDataScope | None = None,
) -> CustomerGroupDetailRead:
    """按范围内父子关系生成稳定层级，并从可见单位计算集团汇总。"""

    if data_scope is None:
        data_scope = AccountDataScope(True, frozenset(), frozenset(), frozenset())
    units = _visible_group_units(group, data_scope)

    headquarters = next((unit for unit in units if unit.is_headquarters), None)
    if headquarters is None:
        raise HTTPException(status_code=409, detail="集团总部数据不完整")

    children_by_parent: dict[UUID, list[CustomerGroupUnit]] = defaultdict(list)
    for unit in units:
        if unit.parent_id is not None:
            children_by_parent[unit.parent_id].append(unit)
    for children in children_by_parent.values():
        children.sort(key=lambda item: item.name)

    ordered_units: list[CustomerGroupUnitRead] = []
    pending: deque[tuple[CustomerGroupUnit, int]] = deque([(headquarters, 0)])
    seen: set[UUID] = set()
    while pending:
        unit, level = pending.popleft()
        if unit.id in seen:
            raise HTTPException(status_code=409, detail="集团层级数据存在循环")
        seen.add(unit.id)
        ordered_units.append(_to_public_unit(unit, level))
        pending.extend((child, level + 1) for child in children_by_parent.get(unit.id, []))
    if len(seen) != len(units):
        raise HTTPException(status_code=409, detail="集团层级数据存在未连接节点")

    branches = [unit for unit in units if not unit.is_headquarters]
    summary = CustomerGroupSummaryRead(
        branch_count=len(branches),
        won_branch_count=sum(unit.is_won for unit in branches),
        active_opportunity_count=sum(
            unit.opportunity_stage is not None and unit.opportunity_stage is not OpportunityStage.closed_lost for unit in units
        ),
        actual_sales_amount=sum((unit.actual_sales_amount for unit in units), start=Decimal(0)),
        provinces=sorted({unit.province for unit in units}),
        cities=sorted({unit.city for unit in units}),
    )
    return CustomerGroupDetailRead(
        id=group.id, name=group.name, color=group.color, headquarters_id=headquarters.id, summary=summary, units=ordered_units,
    )


def get_public_customer_group_detail(
    db: Session,
    group_id: UUID,
    data_scope: AccountDataScope | None = None,
) -> CustomerGroupDetailRead:
    """按集团 ID 读取范围内关系树，越权和不存在统一返回 404。"""

    if data_scope is None:
        data_scope = AccountDataScope(True, frozenset(), frozenset(), frozenset())
    visible_headquarters = exists(select(1).where(
        CustomerGroupUnit.group_id == CustomerGroup.id,
        CustomerGroupUnit.is_headquarters.is_(True),
        location_condition(CustomerGroupUnit.province, CustomerGroupUnit.city, data_scope),
    ))
    group = db.scalar(
        select(CustomerGroup)
        .options(selectinload(CustomerGroup.units))
        .where(CustomerGroup.id == group_id, visible_headquarters)
    )
    if group is None:
        raise HTTPException(status_code=404, detail="未找到该客户集团")
    return build_public_customer_group_detail(group, data_scope)
