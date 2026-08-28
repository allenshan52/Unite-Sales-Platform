"""查询并统一优纳特、同行成交订单，支持后台组合筛选与分页。"""

from datetime import date
from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import extract, select, union_all
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.admin_deal_schemas import (
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
    CompetitorDeal,
    CompetitorDealProduct,
    Opportunity,
    Organization,
    SalesProject,
    SalesProjectProduct,
    Salesperson,
)
from app.services.account_access import (
    AccountDataScope,
    competitor_visibility_condition,
    location_condition,
    unite_deal_visibility_condition,
)

SellerFilter = Literal["all", "unite", "competitor"]


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


def _validate_unite_deal_references(db: Session, payload: AdminUniteDealInput) -> None:
    """确认订单单位、销售和关联商机存在，且商机属于所选单位。"""

    if db.get(Organization, payload.organization_id) is None:
        raise HTTPException(status_code=422, detail="所选成交单位不存在")
    if payload.salesperson_id is not None and db.get(Salesperson, payload.salesperson_id) is None:
        raise HTTPException(status_code=422, detail="所选销售人员不存在")
    if payload.opportunity_id is not None:
        opportunity = db.get(Opportunity, payload.opportunity_id)
        if opportunity is None or opportunity.organization_id != payload.organization_id:
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


def _apply_unite_deal_fields(project: SalesProject, payload: AdminUniteDealInput) -> None:
    """把统一订单表单字段映射到既有优纳特成交项目列。"""

    project.organization_id = payload.organization_id
    project.opportunity_id = payload.opportunity_id
    project.salesperson_id = payload.salesperson_id
    project.name = payload.project_name
    project.contract_amount = payload.total_amount
    project.supplier_name = payload.supplier_name
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


def create_unite_deal(db: Session, payload: AdminUniteDealInput, actor_username: str) -> AdminDealMutationResult:
    """直接在公共成交项目表新增一笔优纳特订单及多条产品。"""

    _validate_unite_deal_references(db, payload)
    project = SalesProject(id=uuid4(), organization_id=payload.organization_id, name=payload.project_name, contract_amount=payload.total_amount)
    _apply_unite_deal_fields(project, payload)
    _sync_unite_deal_products(db, project, payload)
    db.add(project)
    db.add(AuditLog(organization_id=payload.organization_id, actor_username=actor_username, action="新增成交订单", detail={"订单ID": str(project.id)}))
    _commit_unite_deal(db)
    return AdminDealMutationResult(id=project.id)


def update_unite_deal(db: Session, deal_id: UUID, payload: AdminUniteDealInput, actor_username: str) -> AdminDealMutationResult:
    """修改一笔优纳特订单全部字段，并允许调整所属单位。"""

    project = db.scalar(select(SalesProject).options(selectinload(SalesProject.products)).where(SalesProject.id == deal_id))
    if project is None:
        raise HTTPException(status_code=404, detail="未找到该优纳特成交订单")
    _validate_unite_deal_references(db, payload)
    _apply_unite_deal_fields(project, payload)
    _sync_unite_deal_products(db, project, payload)
    db.add(AuditLog(organization_id=payload.organization_id, actor_username=actor_username, action="编辑成交订单", detail={"订单ID": str(project.id), "字段": list(payload.model_fields)}))
    _commit_unite_deal(db)
    return AdminDealMutationResult(id=project.id)


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
    """分别按筛选和账号区域过滤两类订单，再统一排序和分页。"""

    items: list[AdminDealListItem] = []
    keyword = f"%{product.strip()}%" if product and product.strip() else None
    if seller in ("all", "unite") and competitor_id is None:
        unite_conditions = []
        if data_scope is not None:
            unite_conditions.append(unite_deal_visibility_condition(data_scope))
        if supplier:
            unite_conditions.append(SalesProject.supplier_name == supplier)
        if keyword:
            unite_conditions.append(SalesProject.products.any(SalesProjectProduct.product_name.ilike(keyword)))
        if year:
            unite_conditions.append(extract("year", SalesProject.signed_at) == year)
        statement = (
            select(SalesProject, Organization.name, Salesperson.display_name)
            .join(Organization, Organization.id == SalesProject.organization_id)
            .outerjoin(Salesperson, Salesperson.id == SalesProject.salesperson_id)
            .options(selectinload(SalesProject.products))
            .where(*unite_conditions)
        )
        for project_record, customer_name, salesperson_name in db.execute(statement).all():
            items.append(AdminDealListItem(
                id=project_record.id,
                seller_type="unite",
                customer_id=project_record.organization_id,
                seller_name="优纳特",
                customer_name=customer_name,
                project_name=project_record.name,
                total_amount=project_record.contract_amount,
                supplier_name=project_record.supplier_name,
                opportunity_id=project_record.opportunity_id,
                salesperson_id=project_record.salesperson_id,
                salesperson_name=salesperson_name,
                signed_at=project_record.signed_at,
                province=project_record.province,
                city=project_record.city,
                notes=project_record.project_detail,
                products=[_product_read(item) for item in project_record.products],
            ))

    if seller in ("all", "competitor"):
        competitor_conditions = []
        if data_scope is not None:
            competitor_conditions.append(location_condition(CompetitorCustomer.province, CompetitorCustomer.city, data_scope))
        if supplier:
            competitor_conditions.append(CompetitorDeal.supplier_name == supplier)
        if competitor_id:
            competitor_conditions.append(Competitor.id == competitor_id)
        if keyword:
            competitor_conditions.append(CompetitorDeal.products.any(CompetitorDealProduct.product_name.ilike(keyword)))
        if year:
            competitor_conditions.append(extract("year", CompetitorDeal.signed_at) == year)
        statement = (
            select(CompetitorDeal, CompetitorCustomer.name, CompetitorCustomer.province, CompetitorCustomer.city, Competitor.id, Competitor.name)
            .join(CompetitorCustomer, CompetitorCustomer.id == CompetitorDeal.competitor_customer_id)
            .join(Competitor, Competitor.id == CompetitorCustomer.competitor_id)
            .options(selectinload(CompetitorDeal.products))
            .where(*competitor_conditions)
        )
        for deal, customer_name, province, city, seller_id, seller_name in db.execute(statement).all():
            items.append(AdminDealListItem(
                id=deal.id,
                seller_type="competitor",
                seller_id=seller_id,
                customer_id=deal.competitor_customer_id,
                seller_name=seller_name,
                customer_name=customer_name,
                project_name=deal.project_name,
                total_amount=deal.amount,
                supplier_name=deal.supplier_name,
                signed_at=deal.signed_at,
                province=province,
                city=city,
                deal_type=deal.deal_type,
                source_type=deal.source_type,
                source_reference=deal.source_reference,
                source_url=deal.source_url,
                confidence=deal.confidence,
                notes=deal.notes,
                products=[_product_read(item) for item in deal.products],
            ))

    items.sort(key=lambda item: (item.signed_at or date.min, item.project_name, str(item.id)), reverse=True)
    total = len(items)
    offset = (page - 1) * page_size
    return AdminDealPage(items=items[offset:offset + page_size], total=total, page=page, page_size=page_size)


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
    competitor_scope_condition = location_condition(CompetitorCustomer.province, CompetitorCustomer.city, data_scope) if data_scope is not None else None
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
