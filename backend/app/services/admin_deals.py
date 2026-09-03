"""统一查询和写入优纳特、同行成交订单，并负责跨归属事务转换。"""

from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import extract, func, literal, select, union_all
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.admin_deal_schemas import (
    AdminCompetitorDealInput,
    AdminDealFilterOptions,
    AdminDealListItem,
    AdminDealMutationResult,
    AdminDealOption,
    AdminDealPage,
    AdminDealProductRead,
    AdminUniteDealInput,
)
from app.models import (
    AuditLog,
    Competitor,
    CompetitorCustomer,
    CompetitorCustomerLevel,
    CompetitorCustomerOrganizationLink,
    CompetitorDeal,
    CompetitorDealProduct,
    CompetitorMatchStatus,
    CustomerStatus,
    GeocodeStatus,
    IntelligenceConfidence,
    Opportunity,
    Organization,
    OrganizationSite,
    OrganizationType,
    ReviewStatus,
    Salesperson,
    SalesProject,
    SalesProjectProduct,
)
from app.services.account_access import (
    AccountDataScope,
    competitor_order_location_condition,
    competitor_visibility_condition,
    require_competitor_access,
    require_location_access,
    require_organization_access,
    unite_deal_visibility_condition,
)
from app.services.admin_data import sync_competitor_deal_products
from app.services.organizations import normalize_name

SellerFilter = Literal["all", "unite", "competitor"]


def _require_order_target_access(
    db: Session,
    organization_id: UUID,
    province: str | None,
    city: str | None,
    data_scope: AccountDataScope,
) -> None:
    """订单有完整所在地快照时按快照授权，否则按关联单位地点兼容旧数据。"""

    if province and city:
        require_location_access(data_scope, province, city)
    else:
        require_organization_access(db, organization_id, data_scope)


def _product_read(product: object) -> AdminDealProductRead:
    """把两类产品 ORM 记录收敛为同一后台展示结构。"""

    return AdminDealProductRead(
        id=product.id,
        product_name=product.product_name,
        brand=product.brand,
        specification_model=product.specification_model,
        product_image_url=getattr(product, "product_image_url", None),
        unit_price=product.unit_price,
        quantity=product.quantity,
        line_total=product.line_total,
    )


def _resolve_organization(
    db: Session,
    *,
    organization_id: UUID | None,
    organization_name: str | None,
    location_name: str | None,
    province: str | None,
    city: str | None,
    customer_status: CustomerStatus,
    actor_username: str,
) -> Organization:
    """复用同名正式单位；名称未命中时建立带基础地区的待核验主档。"""

    organization = db.get(Organization, organization_id) if organization_id else None
    if organization_id is not None and organization is None:
        raise HTTPException(status_code=422, detail="所选成交单位不存在")
    if organization is None and organization_name:
        organization = db.scalar(
            select(Organization).where(Organization.normalized_name == normalize_name(organization_name)).limit(1)
        )
    if organization is not None:
        if customer_status is CustomerStatus.won:
            organization.customer_status = CustomerStatus.won
        return organization
    if not organization_name:
        raise HTTPException(status_code=422, detail="请输入成交单位")
    if not province or not city:
        raise HTTPException(status_code=422, detail="新成交单位还需填写省份和城市，便于后续审核")
    organization = Organization(
        id=uuid4(),
        name=organization_name,
        normalized_name=normalize_name(organization_name),
        organization_type=OrganizationType.enterprise,
        customer_status=customer_status,
        review_status=ReviewStatus.pending,
        notes="由成交订单自动建立，单位类型、地址和资质待审核。",
        sites=[OrganizationSite(
            id=uuid4(),
            site_name=location_name or "待审核主地点",
            province=province,
            city=city,
            geocode_status=GeocodeStatus.pending,
            is_primary=True,
        )],
    )
    db.add(organization)
    # 审计表只保存外键而没有 ORM 关系，先落主档才能保证 flush 顺序稳定。
    db.flush()
    db.add(AuditLog(
        organization_id=organization.id,
        actor_username=actor_username,
        action="成交订单自动新增待核验单位",
        detail={"单位ID": str(organization.id), "单位名称": organization.name},
    ))
    return organization


def _resolve_competitor(
    db: Session,
    *,
    competitor_id: UUID | None,
    competitor_name: str | None,
    actor_username: str,
) -> Competitor:
    """按 ID 或名称复用同行；新同行以停用状态进入主档等待人工审核。"""

    competitor = db.get(Competitor, competitor_id) if competitor_id else None
    if competitor_id is not None and competitor is None:
        raise HTTPException(status_code=422, detail="所选成交同行不存在")
    if competitor is None and competitor_name:
        competitor = db.scalar(select(Competitor).where(func.lower(Competitor.name) == competitor_name.lower()).limit(1))
    if competitor is not None:
        return competitor
    if not competitor_name:
        raise HTTPException(status_code=422, detail="请输入成交同行")
    competitor = Competitor(
        id=uuid4(),
        name=competitor_name,
        color="#6B7280",
        description="由成交订单自动建立，官网、据点和展示颜色待审核。",
        is_active=False,
    )
    db.add(competitor)
    db.add(AuditLog(
        organization_id=None,
        actor_username=actor_username,
        action="新增同行",
        detail={"资源": "competitors", "记录ID": str(competitor.id), "来源": "成交订单自动建立"},
    ))
    db.flush()
    return competitor


def _resolve_competitor_customer(
    db: Session,
    *,
    competitor: Competitor,
    organization: Organization,
    payload: AdminCompetitorDealInput,
    actor_username: str,
) -> CompetitorCustomer:
    """为同行与正式单位找到或建立情报单位，并保存可审核的单位关联。"""

    customer = db.scalar(
        select(CompetitorCustomer)
        .join(CompetitorCustomerOrganizationLink)
        .where(
            CompetitorCustomer.competitor_id == competitor.id,
            CompetitorCustomerOrganizationLink.organization_id == organization.id,
        )
        .limit(1)
    )
    if customer is None:
        customer = db.scalar(select(CompetitorCustomer).where(
            CompetitorCustomer.competitor_id == competitor.id,
            func.lower(CompetitorCustomer.name) == organization.name.lower(),
        ).limit(1))
    if customer is None:
        primary_site = next((site for site in organization.sites if site.is_primary), None)
        province = primary_site.province if primary_site and primary_site.province else payload.province
        city = primary_site.city if primary_site and primary_site.city else payload.city
        if not province or not city:
            raise HTTPException(status_code=422, detail="新成交单位还需填写省份和城市，便于后续审核")
        customer = CompetitorCustomer(
            id=uuid4(),
            competitor_id=competitor.id,
            name=organization.name,
            customer_level=CompetitorCustomerLevel.level_three,
            address=(primary_site.address or primary_site.raw_address) if primary_site else None,
            province=province,
            city=city,
            longitude=primary_site.longitude if primary_site else None,
            latitude=primary_site.latitude if primary_site else None,
            source_type=payload.source_type or IntelligenceSourceType.inferred,
            source_reference=payload.source_reference or "由成交订单自动建档，来源待补充",
            source_url=payload.source_url,
            confidence=payload.confidence or IntelligenceConfidence.low,
            first_observed_at=payload.signed_at,
            notes="由成交订单自动建立；地址、等级和地图坐标待补充。",
        )
        db.add(customer)
        db.flush()
    link = db.scalar(select(CompetitorCustomerOrganizationLink).where(
        CompetitorCustomerOrganizationLink.competitor_customer_id == customer.id
    ))
    if link is not None and link.organization_id != organization.id:
        raise HTTPException(status_code=409, detail="该同行成交单位已关联其他正式单位，请先完成关联审核")
    if link is None:
        is_verified = organization.review_status is ReviewStatus.verified
        db.add(CompetitorCustomerOrganizationLink(
            id=uuid4(),
            competitor_customer_id=customer.id,
            organization_id=organization.id,
            match_status=CompetitorMatchStatus.confirmed if is_verified else CompetitorMatchStatus.pending,
            match_method="成交订单人工选择" if is_verified else "成交订单自动建档",
            match_confidence=IntelligenceConfidence.high if is_verified else IntelligenceConfidence.medium,
            matched_by=actor_username,
            matched_at=datetime.now(UTC) if is_verified else None,
            notes="新单位需先完成主档核验。" if not is_verified else None,
        ))
    return customer


def _validate_unite_deal_references(db: Session, payload: AdminUniteDealInput, organization: Organization) -> None:
    """确认订单单位、销售和关联商机存在，且商机属于所选单位。"""

    if payload.salesperson_id is not None and db.get(Salesperson, payload.salesperson_id) is None:
        raise HTTPException(status_code=422, detail="所选销售人员不存在")
    if payload.opportunity_id is not None:
        opportunity = db.get(Opportunity, payload.opportunity_id)
        if opportunity is None or opportunity.organization_id != organization.id:
            raise HTTPException(status_code=422, detail="关联商机必须属于所选成交单位")


def _sync_unite_deal_products(db: Session, project: SalesProject, payload: AdminUniteDealInput) -> None:
    """按表单顺序原子同步产品，并拒绝复用其他订单的产品 ID。"""

    existing = {product.id: product for product in project.products}
    retained_ids: set[UUID] = set()
    for position, item in enumerate(payload.products):
        values = item.model_dump(exclude={"id"})
        if item.id is None:
            project.products.append(SalesProjectProduct(id=uuid4(), **values, position=position))
            continue
        product = existing.get(item.id)
        if product is None:
            raise HTTPException(status_code=422, detail="成交产品不属于当前订单")
        retained_ids.add(item.id)
        for field, value in values.items():
            setattr(product, field, value)
        product.position = position
    for product_id, product in existing.items():
        if product_id not in retained_ids:
            db.delete(product)
    first = payload.products[0] if payload.products else None
    project.unit_price = first.unit_price if first else None
    project.quantity = first.quantity if first else None
    project.specification_model = first.specification_model if first else None


def _apply_unite_deal_fields(project: SalesProject, payload: AdminUniteDealInput, organization_id: UUID) -> None:
    """把统一订单表单字段映射到既有优纳特成交项目列。"""

    project.organization_id = organization_id
    project.opportunity_id = payload.opportunity_id
    project.salesperson_id = payload.salesperson_id
    project.name = payload.project_name
    project.contract_amount = payload.total_amount
    project.supplier_name = payload.supplier_name
    project.location_name = payload.location_name
    project.province = payload.province
    project.city = payload.city
    project.signed_at = payload.signed_at
    project.project_detail = payload.notes


def _commit_unite_deal(db: Session) -> None:
    """提交订单级写入，并把数据库约束错误转换为中文业务消息。"""

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="订单与关联数据冲突，请刷新后重试") from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="订单保存失败，请稍后重试") from error


def _stage_unite_deal(
    db: Session,
    payload: AdminUniteDealInput,
    actor_username: str,
    data_scope: AccountDataScope,
) -> SalesProject:
    """暂存一笔新优纳特订单，不提交事务，供新增和跨归属转换共同使用。"""

    organization = _resolve_organization(
        db,
        organization_id=payload.organization_id,
        organization_name=payload.organization_name,
        location_name=payload.location_name,
        province=payload.province,
        city=payload.city,
        customer_status=CustomerStatus.won,
        actor_username=actor_username,
    )
    _require_order_target_access(db, organization.id, payload.province, payload.city, data_scope)
    _validate_unite_deal_references(db, payload, organization)
    project = SalesProject(id=uuid4(), organization_id=organization.id, name=payload.project_name, contract_amount=payload.total_amount)
    _apply_unite_deal_fields(project, payload, organization.id)
    new_payload = payload.model_copy(update={
        "products": [item.model_copy(update={"id": None}) for item in payload.products],
    })
    _sync_unite_deal_products(db, project, new_payload)
    db.add(project)
    return project


def create_unite_deal(
    db: Session,
    payload: AdminUniteDealInput,
    actor_username: str,
    data_scope: AccountDataScope,
) -> AdminDealMutationResult:
    """新增优纳特订单；输入新单位名称时同事务建立待核验正式单位。"""

    project = _stage_unite_deal(db, payload, actor_username, data_scope)
    db.add(AuditLog(organization_id=project.organization_id, actor_username=actor_username, action="新增成交订单", detail={"订单ID": str(project.id)}))
    _commit_unite_deal(db)
    return AdminDealMutationResult(id=project.id)


def update_unite_deal(
    db: Session,
    deal_id: UUID,
    payload: AdminUniteDealInput,
    actor_username: str,
    data_scope: AccountDataScope,
) -> AdminDealMutationResult:
    """修改优纳特订单；更换为新单位名称时原子建立待核验主档。"""

    project = db.scalar(select(SalesProject).options(selectinload(SalesProject.products)).where(SalesProject.id == deal_id))
    if project is None:
        raise HTTPException(status_code=404, detail="未找到该优纳特成交订单")
    organization = _resolve_organization(
        db,
        organization_id=payload.organization_id,
        organization_name=payload.organization_name,
        location_name=payload.location_name,
        province=payload.province,
        city=payload.city,
        customer_status=CustomerStatus.won,
        actor_username=actor_username,
    )
    _require_order_target_access(db, organization.id, payload.province, payload.city, data_scope)
    _validate_unite_deal_references(db, payload, organization)
    _apply_unite_deal_fields(project, payload, organization.id)
    _sync_unite_deal_products(db, project, payload)
    db.add(AuditLog(organization_id=organization.id, actor_username=actor_username, action="编辑成交订单", detail={"订单ID": str(project.id), "字段": list(payload.model_fields)}))
    _commit_unite_deal(db)
    return AdminDealMutationResult(id=project.id)


def _apply_competitor_deal_fields(
    deal: CompetitorDeal,
    customer_id: UUID,
    payload: AdminCompetitorDealInput,
) -> None:
    """把统一同行订单表单映射到既有竞争情报订单列。"""

    deal.competitor_customer_id = customer_id
    deal.project_name = payload.project_name
    deal.deal_type = payload.deal_type
    deal.supplier_name = payload.supplier_name
    deal.amount = payload.amount
    deal.signed_at = payload.signed_at
    deal.location_name = payload.location_name
    deal.province = payload.province
    deal.city = payload.city
    deal.source_type = payload.source_type
    deal.source_reference = payload.source_reference
    deal.source_url = payload.source_url
    deal.confidence = payload.confidence
    deal.notes = payload.notes


def _resolve_competitor_deal_parties(
    db: Session,
    payload: AdminCompetitorDealInput,
    actor_username: str,
    data_scope: AccountDataScope,
) -> CompetitorCustomer:
    """解析同行与正式单位，并确保两个主体都在当前账号可维护范围内。"""

    organization = _resolve_organization(
        db,
        organization_id=payload.organization_id,
        organization_name=payload.organization_name,
        location_name=payload.location_name,
        province=payload.province,
        city=payload.city,
        customer_status=CustomerStatus.potential,
        actor_username=actor_username,
    )
    _require_order_target_access(db, organization.id, payload.province, payload.city, data_scope)
    competitor = _resolve_competitor(
        db,
        competitor_id=payload.competitor_id,
        competitor_name=payload.competitor_name,
        actor_username=actor_username,
    )
    require_competitor_access(db, competitor.id, data_scope, actor_username)
    return _resolve_competitor_customer(
        db,
        competitor=competitor,
        organization=organization,
        payload=payload,
        actor_username=actor_username,
    )


def _stage_competitor_deal(
    db: Session,
    payload: AdminCompetitorDealInput,
    actor_username: str,
    data_scope: AccountDataScope,
) -> tuple[CompetitorDeal, CompetitorCustomer]:
    """暂存一笔新同行订单及其主体关系，不提交事务。"""

    customer = _resolve_competitor_deal_parties(db, payload, actor_username, data_scope)
    deal = CompetitorDeal(id=uuid4(), competitor_customer_id=customer.id)
    _apply_competitor_deal_fields(deal, customer.id, payload)
    products = [item.model_dump(exclude={"id"}) for item in payload.products]
    sync_competitor_deal_products(db, deal, products)
    db.add(deal)
    return deal, customer


def create_competitor_deal(
    db: Session,
    payload: AdminCompetitorDealInput,
    actor_username: str,
    data_scope: AccountDataScope,
) -> AdminDealMutationResult:
    """原子新增同行订单，并按需建立同行、正式单位及其待审核关联。"""

    deal, customer = _stage_competitor_deal(db, payload, actor_username, data_scope)
    db.add(AuditLog(
        organization_id=customer.organization_link.organization_id if customer.organization_link else None,
        actor_username=actor_username,
        action="新增同行成交订单",
        detail={"订单ID": str(deal.id), "同行成交单位ID": str(customer.id)},
    ))
    _commit_unite_deal(db)
    return AdminDealMutationResult(id=deal.id)


def convert_unite_deal_to_competitor(
    db: Session,
    deal_id: UUID,
    payload: AdminCompetitorDealInput,
    actor_username: str,
    data_scope: AccountDataScope,
) -> AdminDealMutationResult:
    """把优纳特订单原子替换为同行订单，任一步失败时保留原订单。"""

    source = db.get(SalesProject, deal_id)
    if source is None:
        raise HTTPException(status_code=404, detail="未找到该优纳特成交订单")
    target, customer = _stage_competitor_deal(db, payload, actor_username, data_scope)
    db.delete(source)
    db.add(AuditLog(
        organization_id=customer.organization_link.organization_id if customer.organization_link else None,
        actor_username=actor_username,
        action="转换订单归属",
        detail={"原归属": "优纳特", "原订单ID": str(deal_id), "新归属": "同行", "新订单ID": str(target.id)},
    ))
    _commit_unite_deal(db)
    return AdminDealMutationResult(id=target.id)


def convert_competitor_deal_to_unite(
    db: Session,
    deal_id: UUID,
    payload: AdminUniteDealInput,
    actor_username: str,
    data_scope: AccountDataScope,
) -> AdminDealMutationResult:
    """把同行订单原子替换为优纳特订单，产品改用目标表的新主键。"""

    source = db.get(CompetitorDeal, deal_id)
    if source is None:
        raise HTTPException(status_code=404, detail="未找到该同行成交订单")
    target = _stage_unite_deal(db, payload, actor_username, data_scope)
    db.delete(source)
    db.add(AuditLog(
        organization_id=target.organization_id,
        actor_username=actor_username,
        action="转换订单归属",
        detail={"原归属": "同行", "原订单ID": str(deal_id), "新归属": "优纳特", "新订单ID": str(target.id)},
    ))
    _commit_unite_deal(db)
    return AdminDealMutationResult(id=target.id)


def update_competitor_deal(
    db: Session,
    deal_id: UUID,
    payload: AdminCompetitorDealInput,
    actor_username: str,
    data_scope: AccountDataScope,
) -> AdminDealMutationResult:
    """修改同行订单及两个主体引用，并原子同步产品明细。"""

    deal = db.scalar(select(CompetitorDeal).options(selectinload(CompetitorDeal.products)).where(CompetitorDeal.id == deal_id))
    if deal is None:
        raise HTTPException(status_code=404, detail="未找到该同行成交订单")
    customer = _resolve_competitor_deal_parties(db, payload, actor_username, data_scope)
    _apply_competitor_deal_fields(deal, customer.id, payload)
    sync_competitor_deal_products(db, deal, [item.model_dump() for item in payload.products])
    db.add(AuditLog(
        organization_id=customer.organization_link.organization_id if customer.organization_link else None,
        actor_username=actor_username,
        action="编辑同行成交订单",
        detail={"订单ID": str(deal.id), "同行成交单位ID": str(customer.id)},
    ))
    _commit_unite_deal(db)
    return AdminDealMutationResult(id=deal.id)


def delete_unite_deal(db: Session, deal_id: UUID, actor_username: str) -> None:
    """永久删除管理员确认的一笔优纳特订单及其级联产品。"""

    project = db.get(SalesProject, deal_id)
    if project is None:
        raise HTTPException(status_code=404, detail="未找到该优纳特成交订单")
    organization_id = project.organization_id
    db.delete(project)
    db.add(AuditLog(organization_id=organization_id, actor_username=actor_username, action="删除成交订单", detail={"订单ID": str(deal_id)}))
    _commit_unite_deal(db)


def list_admin_deals(
    db: Session,
    *,
    seller: SellerFilter,
    supplier: str | None,
    competitor_id: UUID | None,
    product: str | None,
    year: int | None,
    page: int,
    page_size: int,
    data_scope: AccountDataScope | None = None,
) -> AdminDealPage:
    """先在数据库合并轻量订单键并分页，再仅加载当前页详情，避免全量 ORM 实例占用内存。"""

    keyword = f"%{product.strip()}%" if product and product.strip() else None
    start_date = date(year, 1, 1) if year else None
    end_date = date(year + 1, 1, 1) if year else None
    key_statements = []
    if seller in ("all", "unite") and competitor_id is None:
        unite_conditions = []
        if data_scope is not None:
            unite_conditions.append(unite_deal_visibility_condition(data_scope))
        if supplier:
            unite_conditions.append(SalesProject.supplier_name == supplier)
        if keyword:
            unite_conditions.append(SalesProject.products.any(SalesProjectProduct.product_name.ilike(keyword)))
        if start_date and end_date:
            unite_conditions.extend((SalesProject.signed_at >= start_date, SalesProject.signed_at < end_date))
        key_statements.append(
            select(
                literal("unite").label("seller_type"),
                SalesProject.id.label("deal_id"),
                SalesProject.signed_at.label("signed_at"),
                SalesProject.name.label("project_name"),
            )
            .where(*unite_conditions)
        )

    if seller in ("all", "competitor"):
        competitor_conditions = []
        if data_scope is not None:
            competitor_conditions.append(competitor_order_location_condition(data_scope))
        if supplier:
            competitor_conditions.append(CompetitorDeal.supplier_name == supplier)
        if competitor_id:
            competitor_conditions.append(Competitor.id == competitor_id)
        if keyword:
            competitor_conditions.append(CompetitorDeal.products.any(CompetitorDealProduct.product_name.ilike(keyword)))
        if start_date and end_date:
            competitor_conditions.extend((CompetitorDeal.signed_at >= start_date, CompetitorDeal.signed_at < end_date))
        key_statements.append(
            select(
                literal("competitor").label("seller_type"),
                CompetitorDeal.id.label("deal_id"),
                CompetitorDeal.signed_at.label("signed_at"),
                CompetitorDeal.project_name.label("project_name"),
            )
            .join(CompetitorCustomer, CompetitorCustomer.id == CompetitorDeal.competitor_customer_id)
            .join(Competitor, Competitor.id == CompetitorCustomer.competitor_id)
            .where(*competitor_conditions)
        )

    if not key_statements:
        return AdminDealPage(items=[], total=0, page=page, page_size=page_size)
    key_union = (
        key_statements[0].subquery("admin_deal_keys")
        if len(key_statements) == 1
        else union_all(*key_statements).subquery("admin_deal_keys")
    )
    total = int(db.scalar(select(func.count()).select_from(key_union)) or 0)
    if total == 0:
        return AdminDealPage(items=[], total=0, page=page, page_size=page_size)
    page_rows = db.execute(
        select(key_union.c.seller_type, key_union.c.deal_id)
        .order_by(
            key_union.c.signed_at.desc().nullslast(),
            key_union.c.project_name.desc(),
            key_union.c.deal_id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    unite_ids = [row.deal_id for row in page_rows if row.seller_type == "unite"]
    competitor_ids = [row.deal_id for row in page_rows if row.seller_type == "competitor"]
    items_by_key: dict[tuple[str, UUID], AdminDealListItem] = {}

    if unite_ids:
        unite_statement = (
            select(SalesProject, Organization.name, Salesperson.display_name)
            .join(Organization, Organization.id == SalesProject.organization_id)
            .outerjoin(Salesperson, Salesperson.id == SalesProject.salesperson_id)
            .options(selectinload(SalesProject.products))
            .where(SalesProject.id.in_(unite_ids))
        )
        for project_record, customer_name, salesperson_name in db.execute(unite_statement).all():
            items_by_key[("unite", project_record.id)] = AdminDealListItem(
                id=project_record.id,
                seller_type="unite",
                customer_id=project_record.organization_id,
                organization_id=project_record.organization_id,
                seller_name="优纳特",
                customer_name=customer_name,
                project_name=project_record.name,
                total_amount=project_record.contract_amount,
                supplier_name=project_record.supplier_name,
                opportunity_id=project_record.opportunity_id,
                salesperson_id=project_record.salesperson_id,
                salesperson_name=salesperson_name,
                signed_at=project_record.signed_at,
                location_name=project_record.location_name,
                province=project_record.province,
                city=project_record.city,
                notes=project_record.project_detail,
                products=[_product_read(item) for item in project_record.products],
            )

    if competitor_ids:
        competitor_statement = (
            select(
                CompetitorDeal,
                CompetitorCustomer.name,
                CompetitorCustomer.province,
                CompetitorCustomer.city,
                Competitor.id,
                Competitor.name,
                CompetitorCustomerOrganizationLink.organization_id,
            )
            .join(CompetitorCustomer, CompetitorCustomer.id == CompetitorDeal.competitor_customer_id)
            .join(Competitor, Competitor.id == CompetitorCustomer.competitor_id)
            .outerjoin(
                CompetitorCustomerOrganizationLink,
                CompetitorCustomerOrganizationLink.competitor_customer_id == CompetitorCustomer.id,
            )
            .options(selectinload(CompetitorDeal.products))
            .where(CompetitorDeal.id.in_(competitor_ids))
        )
        for deal, customer_name, province, city, seller_id, seller_name, organization_id in db.execute(competitor_statement).all():
            use_customer_location = deal.province is None and deal.city is None
            items_by_key[("competitor", deal.id)] = AdminDealListItem(
                id=deal.id,
                seller_type="competitor",
                seller_id=seller_id,
                customer_id=deal.competitor_customer_id,
                organization_id=organization_id,
                seller_name=seller_name,
                customer_name=customer_name,
                project_name=deal.project_name,
                total_amount=deal.amount,
                supplier_name=deal.supplier_name,
                signed_at=deal.signed_at,
                location_name=deal.location_name,
                province=province if use_customer_location else deal.province,
                city=city if use_customer_location else deal.city,
                deal_type=deal.deal_type,
                source_type=deal.source_type,
                source_reference=deal.source_reference,
                source_url=deal.source_url,
                confidence=deal.confidence,
                notes=deal.notes,
                products=[_product_read(item) for item in deal.products],
            )

    # 分页键查询与详情查询之间若恰好发生并发删除，跳过缺失项而不是让列表接口返回 500。
    items = [
        item
        for row in page_rows
        if (item := items_by_key.get((row.seller_type, row.deal_id))) is not None
    ]
    return AdminDealPage(items=items, total=total, page=page, page_size=page_size)


def get_admin_deal_filter_options(db: Session, data_scope: AccountDataScope | None = None) -> AdminDealFilterOptions:
    """从账号范围内实际订单生成同行、供应商和年份筛选项。"""

    competitor_statement = select(Competitor).order_by(Competitor.name)
    if data_scope is not None:
        competitor_statement = competitor_statement.where(competitor_visibility_condition(data_scope))
    competitors = [
        AdminDealOption(value=str(item.id), label=item.name)
        for item in db.scalars(competitor_statement).all()
    ]
    unite_scope_condition = unite_deal_visibility_condition(data_scope) if data_scope is not None else None
    competitor_scope_condition = competitor_order_location_condition(data_scope) if data_scope is not None else None
    unite_supplier_statement = select(SalesProject.supplier_name.label("supplier")).where(SalesProject.supplier_name.is_not(None))
    competitor_supplier_statement = (
        select(CompetitorDeal.supplier_name.label("supplier"))
        .join(CompetitorCustomer, CompetitorCustomer.id == CompetitorDeal.competitor_customer_id)
        .where(CompetitorDeal.supplier_name.is_not(None))
    )
    if unite_scope_condition is not None:
        unite_supplier_statement = unite_supplier_statement.where(unite_scope_condition)
    if competitor_scope_condition is not None:
        competitor_supplier_statement = competitor_supplier_statement.where(competitor_scope_condition)
    supplier_union = union_all(
        unite_supplier_statement,
        competitor_supplier_statement,
    ).subquery()
    suppliers = [
        str(value)
        for value in db.scalars(
            select(supplier_union.c.supplier).distinct().order_by(supplier_union.c.supplier)
        ).all()
        if value
    ]
    unite_year_statement = select(extract("year", SalesProject.signed_at).label("year")).where(SalesProject.signed_at.is_not(None))
    competitor_year_statement = (
        select(extract("year", CompetitorDeal.signed_at).label("year"))
        .join(CompetitorCustomer, CompetitorCustomer.id == CompetitorDeal.competitor_customer_id)
        .where(CompetitorDeal.signed_at.is_not(None))
    )
    if unite_scope_condition is not None:
        unite_year_statement = unite_year_statement.where(unite_scope_condition)
    if competitor_scope_condition is not None:
        competitor_year_statement = competitor_year_statement.where(competitor_scope_condition)
    year_union = union_all(unite_year_statement, competitor_year_statement).subquery()
    years = [
        int(value)
        for value in db.scalars(
            select(year_union.c.year).distinct().order_by(year_union.c.year)
        ).all()
        if value is not None
    ]
    return AdminDealFilterOptions(competitors=competitors, suppliers=suppliers, years=list(reversed(years)))
