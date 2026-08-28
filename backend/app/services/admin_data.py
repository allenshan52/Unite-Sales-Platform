"""管理员数据后台服务：通过显式资源白名单复用分页、校验、CRUD 与审计。"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from geoalchemy2.elements import WKTElement
from pydantic import BaseModel, ValidationError
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.admin_data_schemas import (
    AdminDataOption,
    AdminDataPage,
    ChannelPartnerAdminInput,
    CompetitorAdminInput,
    CompetitorCustomerAdminInput,
    CompetitorDealAdminInput,
    CompetitorLinkAdminInput,
    CompetitorSiteAdminInput,
    CompetitorStrengthRegionAdminInput,
    CustomerGroupAdminInput,
    CustomerGroupUnitAdminInput,
    SalesActivityAdminInput,
    SalesOfficeAdminInput,
    SalespersonAdminInput,
    SalespersonCoverageScopeAdminInput,
)
from app.models import (
    AuditLog,
    ChannelPartnerLocation,
    ChannelPartnerType,
    Competitor,
    CompetitorCustomer,
    CompetitorCustomerOrganizationLink,
    CompetitorDeal,
    CompetitorDealProduct,
    CompetitorSite,
    CompetitorStrengthRegion,
    CustomerGroup,
    CustomerGroupUnit,
    Organization,
    OrganizationSite,
    SalesActivity,
    SalesOfficeLocation,
    Salesperson,
    SalespersonCoverageScope,
)
from app.sales_coverage import SalesCoverageLevel
from app.services.account_access import (
    AccountDataScope,
    competitor_visibility_condition,
    coverage_scope_is_visible,
    customer_group_visibility_condition,
    location_condition,
    location_is_visible,
    organization_visibility_condition,
    require_competitor_access,
    require_location_access,
)
from app.services.geocoding import gcj02_to_wgs84


@dataclass(frozen=True)
class ResourceDefinition:
    """声明一个允许后台写入的 ORM 模型、输入模式和可检索字段。"""

    model: type[Any]
    schema: type[BaseModel]
    label: str
    option_label: str
    search_fields: tuple[str, ...]
    foreign_keys: dict[str, str] = field(default_factory=dict)


RESOURCE_DEFINITIONS: dict[str, ResourceDefinition] = {
    "sales_office_locations": ResourceDefinition(SalesOfficeLocation, SalesOfficeAdminInput, "销售常驻点", "name", ("name", "city", "address")),
    "channel_partners": ResourceDefinition(ChannelPartnerLocation, ChannelPartnerAdminInput, "渠道合作方", "name", ("name", "address", "authorized_coverage_area")),
    "customer_groups": ResourceDefinition(CustomerGroup, CustomerGroupAdminInput, "客户集团", "name", ("name",)),
    "customer_group_units": ResourceDefinition(CustomerGroupUnit, CustomerGroupUnitAdminInput, "集团单位", "name", ("name", "address", "province", "city"), {"group_id": "customer_groups", "parent_id": "customer_group_units"}),
    "competitors": ResourceDefinition(Competitor, CompetitorAdminInput, "同行", "name", ("name", "website_url", "description")),
    "competitor_sites": ResourceDefinition(CompetitorSite, CompetitorSiteAdminInput, "同行据点", "name", ("name", "address", "province", "city"), {"competitor_id": "competitors"}),
    "competitor_customers": ResourceDefinition(CompetitorCustomer, CompetitorCustomerAdminInput, "同行成交单位", "name", ("name", "address", "province", "city"), {"competitor_id": "competitors"}),
    "competitor_deals": ResourceDefinition(CompetitorDeal, CompetitorDealAdminInput, "同行成交记录", "project_name", ("project_name", "deal_type", "supplier_name", "source_reference"), {"competitor_customer_id": "competitor_customers"}),
    "competitor_strength_regions": ResourceDefinition(CompetitorStrengthRegion, CompetitorStrengthRegionAdminInput, "同行强势区域", "province", ("province", "city", "basis"), {"competitor_id": "competitors"}),
    "competitor_links": ResourceDefinition(CompetitorCustomerOrganizationLink, CompetitorLinkAdminInput, "同行正式单位关联", "match_method", ("match_method", "matched_by", "notes"), {"competitor_customer_id": "competitor_customers", "organization_id": "organizations"}),
    "salespeople": ResourceDefinition(Salesperson, SalespersonAdminInput, "销售人员", "display_name", ("employee_code", "display_name")),
    "salesperson_coverage_cities": ResourceDefinition(SalespersonCoverageScope, SalespersonCoverageScopeAdminInput, "销售覆盖范围", "scope_name", ("scope_name", "province", "city", "amap_adcode"), {"salesperson_id": "salespeople"}),
    "sales_activities": ResourceDefinition(SalesActivity, SalesActivityAdminInput, "销售活动", "city", ("province", "city", "amap_adcode", "notes"), {"salesperson_id": "salespeople", "organization_id": "organizations"}),
}

OPTION_DEFINITIONS: dict[str, tuple[type[Any], str, tuple[str, ...]]] = {
    key: (definition.model, definition.option_label, definition.search_fields)
    for key, definition in RESOURCE_DEFINITIONS.items()
}
OPTION_DEFINITIONS["organizations"] = (Organization, "name", ("name",))

# 详情工作区只允许通过显式父键读取子资源，禁止客户端把任意字段拼进查询。
PARENT_SCOPE_FIELDS: dict[str, str] = {
    "competitor_sites": "competitor_id",
    "competitor_customers": "competitor_id",
    "competitor_deals": "competitor_customer_id",
    "competitor_strength_regions": "competitor_id",
    "competitor_links": "competitor_customer_id",
}

SALESPERSON_ADMIN_RESOURCES = frozenset({"salespeople", "salesperson_coverage_cities", "sales_activities"})


def _definition(resource: str) -> ResourceDefinition:
    """只允许注册表中的资源进入通用 CRUD，阻止客户端选择任意数据库表。"""

    definition = RESOURCE_DEFINITIONS.get(resource)
    if definition is None:
        raise HTTPException(status_code=404, detail="未找到该后台数据类型")
    return definition


def ensure_admin_data_resource_access(resource: str, scope: AccountDataScope) -> None:
    """销售主档及子资源只允许全国账号和超管通过通用后台接口访问。"""

    if resource in SALESPERSON_ADMIN_RESOURCES and not scope.unrestricted:
        raise HTTPException(status_code=403, detail="当前账号没有销售数据库管理权限")


def validate_admin_data(resource: str, data: dict[str, Any]) -> dict[str, Any]:
    """使用资源专属 Pydantic 模式校验完整表单，并返回 ORM 可接受的值。"""

    try:
        return _definition(resource).schema.model_validate(data).model_dump()
    except ValidationError as error:
        first = error.errors(include_url=False)[0]
        field_name = ".".join(str(part) for part in first["loc"])
        raise HTTPException(status_code=422, detail=f"字段 {field_name or 'data'}：{first['msg']}") from error


def _search_conditions(definition: ResourceDefinition, search: str) -> list[Any]:
    """把一个搜索词限制在资源声明的文本列中，避免动态列名进入 SQL。"""

    keyword = f"%{search.strip()}%"
    return [getattr(definition.model, name).ilike(keyword) for name in definition.search_fields]


def _salesperson_scope_condition(scope: AccountDataScope):
    """把销售人员覆盖与活动位置转换为账号区域交集条件。"""

    coverage_conditions = [location_condition(SalespersonCoverageScope.province, SalespersonCoverageScope.city, scope)]
    if scope.regions:
        coverage_conditions.append(and_(
            SalespersonCoverageScope.scope_level == SalesCoverageLevel.region,
            SalespersonCoverageScope.scope_name.in_(scope.regions),
        ))
    return or_(
        exists(select(1).where(
            SalespersonCoverageScope.salesperson_id == Salesperson.id,
            or_(*coverage_conditions),
        )),
        exists(select(1).where(
            SalesActivity.salesperson_id == Salesperson.id,
            location_condition(SalesActivity.province, SalesActivity.city, scope),
        )),
    )


def _resource_scope_condition(
    resource: str,
    scope: AccountDataScope,
    actor_username: str | None = None,
):
    """返回资源与账号区域的 SQL 交集；无可靠地点字段的资源只做全局只读。"""

    if scope.unrestricted:
        return None
    if resource == "organizations":
        return organization_visibility_condition(scope)
    if resource == "customer_groups":
        return customer_group_visibility_condition(scope)
    if resource == "customer_group_units":
        return location_condition(CustomerGroupUnit.province, CustomerGroupUnit.city, scope)
    if resource == "competitors":
        return competitor_visibility_condition(scope, actor_username)
    if resource == "competitor_sites":
        return location_condition(CompetitorSite.province, CompetitorSite.city, scope)
    if resource == "competitor_customers":
        return location_condition(CompetitorCustomer.province, CompetitorCustomer.city, scope)
    if resource == "competitor_deals":
        return exists(select(1).where(
            CompetitorCustomer.id == CompetitorDeal.competitor_customer_id,
            location_condition(CompetitorCustomer.province, CompetitorCustomer.city, scope),
        ))
    if resource == "competitor_strength_regions":
        return location_condition(CompetitorStrengthRegion.province, CompetitorStrengthRegion.city, scope)
    if resource == "competitor_links":
        return or_(
            exists(select(1).where(
                CompetitorCustomer.id == CompetitorCustomerOrganizationLink.competitor_customer_id,
                location_condition(CompetitorCustomer.province, CompetitorCustomer.city, scope),
            )),
            exists(select(1).where(
                OrganizationSite.organization_id == CompetitorCustomerOrganizationLink.organization_id,
                location_condition(OrganizationSite.province, OrganizationSite.city, scope),
            )),
        )
    if resource == "salespeople":
        return _salesperson_scope_condition(scope)
    if resource == "salesperson_coverage_cities":
        conditions = [location_condition(SalespersonCoverageScope.province, SalespersonCoverageScope.city, scope)]
        if scope.regions:
            conditions.append(and_(SalespersonCoverageScope.scope_level == SalesCoverageLevel.region, SalespersonCoverageScope.scope_name.in_(scope.regions)))
        return or_(*conditions)
    if resource == "sales_activities":
        return location_condition(SalesActivity.province, SalesActivity.city, scope)
    return None


def _related_location_is_visible(
    db: Session,
    model: type[Any],
    record_id: UUID,
    scope: AccountDataScope,
) -> bool:
    """读取父记录省市并按统一口径判断，供无自身地点的子记录写入校验。"""

    row = db.execute(select(model.province, model.city).where(model.id == record_id)).one_or_none()
    return row is not None and location_is_visible(scope, row.province, row.city)


def _coverage_values_are_visible(values: dict[str, Any], scope: AccountDataScope) -> bool:
    """判断一条销售覆盖范围是否与当前账号市、省或大区权限相交。"""

    return coverage_scope_is_visible(
        scope,
        values["scope_level"],
        values["scope_name"],
        values.get("province"),
        values.get("city"),
    )


def ensure_admin_data_mutation_allowed(
    db: Session,
    resource: str,
    record_id: UUID | None,
    values: dict[str, Any],
    scope: AccountDataScope,
    actor_username: str,
) -> None:
    """在通用 CRUD 写入前同时校验旧记录和目标关联，阻止伪造表单越区。"""

    definition = _definition(resource)
    ensure_admin_data_resource_access(resource, scope)
    if scope.unrestricted:
        return
    if resource in {"sales_office_locations", "channel_partners", "customer_groups", "salespeople"}:
        raise HTTPException(status_code=403, detail="该数据缺少单条区域归属，仅超级管理员可在此修改")
    if record_id is not None:
        condition = _resource_scope_condition(resource, scope, actor_username)
        visible_id = db.scalar(select(definition.model.id).where(definition.model.id == record_id, condition)) if condition is not None else None
        if visible_id is None:
            raise HTTPException(status_code=403, detail="当前账号不能修改该区域的数据")
    if resource == "competitors":
        return
    if not values:
        return
    if resource in {"customer_group_units", "competitor_sites", "competitor_customers", "competitor_strength_regions", "sales_activities"}:
        require_location_access(scope, values.get("province"), values.get("city"))
    if resource in {"competitor_sites", "competitor_customers", "competitor_strength_regions"}:
        require_competitor_access(db, values["competitor_id"], scope, actor_username)
    elif resource == "competitor_deals":
        if not _related_location_is_visible(db, CompetitorCustomer, values["competitor_customer_id"], scope):
            raise HTTPException(status_code=403, detail="当前账号不能修改该区域的数据")
    elif resource == "competitor_links":
        customer_visible = _related_location_is_visible(db, CompetitorCustomer, values["competitor_customer_id"], scope)
        organization_visible = db.scalar(select(Organization.id).where(
            Organization.id == values["organization_id"],
            organization_visibility_condition(scope),
        )) is not None
        if not customer_visible and not organization_visible:
            raise HTTPException(status_code=403, detail="当前账号不能修改该区域的数据")
    elif resource == "salesperson_coverage_cities" and not _coverage_values_are_visible(values, scope):
        raise HTTPException(status_code=403, detail="当前账号不能修改该销售覆盖范围")


def _record_fields(definition: ResourceDefinition) -> tuple[str, ...]:
    """从输入模式派生可编辑列，并附加统一只读主键和时间字段。"""

    readonly = tuple(name for name in ("id", "created_at", "updated_at") if hasattr(definition.model, name))
    return readonly + tuple(definition.schema.model_fields)


def _foreign_labels(db: Session, definition: ResourceDefinition, records: list[Any]) -> dict[str, dict[UUID, str]]:
    """批量读取当前页外键名称，列表不逐行触发父记录查询。"""

    labels: dict[str, dict[UUID, str]] = {}
    for field_name, target_resource in definition.foreign_keys.items():
        values = {getattr(record, field_name) for record in records if getattr(record, field_name) is not None}
        if not values:
            labels[field_name] = {}
            continue
        target_model, label_field, _search_fields = OPTION_DEFINITIONS[target_resource]
        rows = db.execute(
            select(target_model.id, getattr(target_model, label_field)).where(target_model.id.in_(values))
        ).all()
        labels[field_name] = {row_id: str(label) for row_id, label in rows}
    return labels


def _serialize_records(db: Session, definition: ResourceDefinition, records: list[Any]) -> list[dict[str, Any]]:
    """输出当前资源的业务字段，并为外键追加同名 `_label` 可读值。"""

    foreign_labels = _foreign_labels(db, definition, records)
    items: list[dict[str, Any]] = []
    for record in records:
        item = {name: getattr(record, name) for name in _record_fields(definition) if name != "products"}
        if definition.model is CompetitorDeal:
            item["products"] = [
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
                for product in record.products
            ]
        for field_name, labels in foreign_labels.items():
            value = getattr(record, field_name)
            item[f"{field_name}_label"] = labels.get(value) if value is not None else None
        items.append(item)
    return items


def list_admin_data(
    db: Session,
    resource: str,
    *,
    page: int,
    page_size: int,
    search: str | None,
    partner_type: ChannelPartnerType | None = None,
    parent_id: UUID | None = None,
    data_scope: AccountDataScope | None = None,
    actor_username: str | None = None,
) -> AdminDataPage:
    """分页读取账号范围内白名单数据；受控分类与父记录筛选先进入 SQL。"""

    definition = _definition(resource)
    if data_scope is not None:
        ensure_admin_data_resource_access(resource, data_scope)
    conditions = []
    if data_scope is not None:
        scope_condition = _resource_scope_condition(resource, data_scope, actor_username)
        if scope_condition is not None:
            conditions.append(scope_condition)
    if partner_type is not None:
        if definition.model is not ChannelPartnerLocation:
            raise HTTPException(status_code=400, detail="该数据类型不支持渠道主体筛选")
        conditions.append(ChannelPartnerLocation.partner_type == partner_type)
    if parent_id is not None:
        parent_field = PARENT_SCOPE_FIELDS.get(resource)
        if parent_field is None:
            raise HTTPException(status_code=400, detail="该数据类型不支持父记录筛选")
        conditions.append(getattr(definition.model, parent_field) == parent_id)
    if search and search.strip():
        conditions.append(or_(*_search_conditions(definition, search)))
    count_statement = select(func.count()).select_from(definition.model).where(*conditions)
    order_columns = []
    if hasattr(definition.model, "updated_at"):
        order_columns.append(definition.model.updated_at.desc())
    order_columns.append(definition.model.id.desc())
    statement = select(definition.model)
    if definition.model is CompetitorDeal:
        statement = statement.options(selectinload(CompetitorDeal.products))
    records = list(db.scalars(
        statement
        .where(*conditions)
        .order_by(*order_columns)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all())
    return AdminDataPage(
        items=_serialize_records(db, definition, records),
        total=db.scalar(count_statement) or 0,
        page=page,
        page_size=page_size,
    )


def list_admin_data_options(
    db: Session,
    resource: str,
    *,
    search: str | None,
    selected_id: UUID | None,
    data_scope: AccountDataScope | None = None,
    actor_username: str | None = None,
) -> list[AdminDataOption]:
    """按账号范围搜索最多 40 个外键选项，并确保授权已选值仍可显示。"""

    option_definition = OPTION_DEFINITIONS.get(resource)
    if option_definition is None:
        raise HTTPException(status_code=404, detail="未找到该关联数据类型")
    if data_scope is not None:
        ensure_admin_data_resource_access(resource, data_scope)
    model, label_field, search_fields = option_definition
    statement = select(model.id, getattr(model, label_field))
    scope_condition = _resource_scope_condition(resource, data_scope, actor_username) if data_scope is not None else None
    if scope_condition is not None:
        statement = statement.where(scope_condition)
    if search and search.strip():
        keyword = f"%{search.strip()}%"
        statement = statement.where(or_(*(getattr(model, name).ilike(keyword) for name in search_fields)))
    rows = list(db.execute(statement.order_by(getattr(model, label_field)).limit(40)).all())
    if selected_id is not None and all(row_id != selected_id for row_id, _label in rows):
        selected_statement = select(model.id, getattr(model, label_field)).where(model.id == selected_id)
        if scope_condition is not None:
            selected_statement = selected_statement.where(scope_condition)
        selected = db.execute(selected_statement).one_or_none()
        if selected is not None:
            rows.append(selected)
    return [AdminDataOption(value=row_id, label=str(label)) for row_id, label in rows]


def _validate_group_parent(db: Session, values: dict[str, Any], record_id: UUID | None) -> None:
    """阻止跨集团父节点、自引用及沿父链形成的循环。"""

    parent_id = values.get("parent_id")
    if parent_id is None:
        return
    if record_id is not None and parent_id == record_id:
        raise HTTPException(status_code=422, detail="集团单位不能把自己设为父节点")
    parent = db.get(CustomerGroupUnit, parent_id)
    if parent is None or parent.group_id != values["group_id"]:
        raise HTTPException(status_code=422, detail="父节点必须属于同一客户集团")
    seen: set[UUID] = set()
    while parent is not None and parent.parent_id is not None:
        if record_id is not None and parent.parent_id == record_id:
            raise HTTPException(status_code=422, detail="集团层级不能形成循环")
        if parent.id in seen:
            raise HTTPException(status_code=409, detail="现有集团层级数据存在循环")
        seen.add(parent.id)
        parent = db.get(CustomerGroupUnit, parent.parent_id)


def _prepare_values(db: Session, definition: ResourceDefinition, values: dict[str, Any], record_id: UUID | None) -> dict[str, Any]:
    """补充数据库专用空间字段，并执行无法只靠单行模式表达的层级校验。"""

    prepared = dict(values)
    if definition.model is CustomerGroupUnit:
        _validate_group_parent(db, prepared, record_id)
        longitude, latitude = gcj02_to_wgs84(prepared["longitude"], prepared["latitude"])
        prepared["location"] = WKTElement(f"POINT({longitude} {latitude})", srid=4326)
    return prepared


def _sync_competitor_deal_products(db: Session, record: CompetitorDeal, payloads: list[dict[str, Any]]) -> None:
    """同步同行订单产品集合，并按提交顺序生成稳定展示位置。"""

    existing = {product.id: product for product in record.products}
    retained_ids: set[UUID] = set()
    for position, payload in enumerate(payloads):
        values = dict(payload)
        product_id = values.pop("id", None)
        if product_id is None:
            record.products.append(CompetitorDealProduct(id=uuid4(), **values, position=position))
            continue
        product = existing.get(product_id)
        if product is None:
            raise HTTPException(status_code=422, detail="成交产品不属于当前同行订单")
        retained_ids.add(product_id)
        for field, value in values.items():
            setattr(product, field, value)
        product.position = position
    for product_id, product in existing.items():
        if product_id not in retained_ids:
            db.delete(product)


def _normalize_competitor_product_values(values: dict[str, Any], payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """兼容旧单产品表单，并让主表兼容列始终镜像第一条产品。"""

    if not payloads and values.get("product_name"):
        payloads = [{
            "id": None,
            "product_name": values["product_name"],
            "specification_model": values.get("specification_model"),
            "product_image_url": values.get("product_image_url"),
            "unit_price": values.get("unit_price"),
            "quantity": values.get("quantity"),
            "line_total": values["amount"],
        }]
    if payloads:
        first = payloads[0]
        for field in ("product_name", "specification_model", "product_image_url", "unit_price", "quantity"):
            values[field] = first.get(field)
    return payloads


def _commit_or_error(db: Session) -> None:
    """统一提交并把数据库约束错误转换为不泄露内部 SQL 的中文响应。"""

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="数据与现有记录重复或仍被其他记录引用，请核对后重试") from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="数据库操作失败，请稍后重试") from error


def create_admin_data(db: Session, resource: str, values: dict[str, Any], actor_username: str) -> dict[str, Any]:
    """新增一条完整业务记录并写入通用管理员审计日志。"""

    definition = _definition(resource)
    prepared = _prepare_values(db, definition, values, None)
    product_payloads = prepared.pop("products", []) if definition.model is CompetitorDeal else []
    if definition.model is CompetitorDeal:
        product_payloads = _normalize_competitor_product_values(prepared, product_payloads)
    record = definition.model(id=uuid4(), **prepared)
    if definition.model is CompetitorDeal:
        _sync_competitor_deal_products(db, record, product_payloads)
    db.add(record)
    db.add(AuditLog(
        organization_id=None,
        actor_username=actor_username,
        action=f"新增{definition.label}",
        detail={"资源": resource, "记录ID": str(record.id)},
    ))
    _commit_or_error(db)
    db.refresh(record)
    return _serialize_records(db, definition, [record])[0]


def update_admin_data(
    db: Session,
    resource: str,
    record_id: UUID,
    values: dict[str, Any],
    actor_username: str,
) -> dict[str, Any]:
    """以完整表单覆盖一条业务记录，禁止修改主键和系统时间。"""

    definition = _definition(resource)
    record = db.get(definition.model, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"未找到该{definition.label}")
    prepared = _prepare_values(db, definition, values, record_id)
    product_payloads = prepared.pop("products", None) if definition.model is CompetitorDeal else None
    if definition.model is CompetitorDeal and product_payloads is not None:
        product_payloads = _normalize_competitor_product_values(prepared, product_payloads)
    for name, value in prepared.items():
        setattr(record, name, value)
    if product_payloads is not None:
        _sync_competitor_deal_products(db, record, product_payloads)
    db.add(AuditLog(
        organization_id=None,
        actor_username=actor_username,
        action=f"编辑{definition.label}",
        detail={"资源": resource, "记录ID": str(record.id), "字段": list(values)},
    ))
    _commit_or_error(db)
    db.refresh(record)
    return _serialize_records(db, definition, [record])[0]


def delete_admin_data(db: Session, resource: str, record_id: UUID, actor_username: str) -> None:
    """永久删除一条白名单业务记录，并依赖既有外键约束保护关联完整性。"""

    definition = _definition(resource)
    record = db.get(definition.model, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"未找到该{definition.label}")
    db.delete(record)
    db.add(AuditLog(
        organization_id=None,
        actor_username=actor_username,
        action=f"删除{definition.label}",
        detail={"资源": resource, "记录ID": str(record_id)},
    ))
    _commit_or_error(db)
