"""典型案例服务：聚合省级公开地图，并原子维护去敏案例与成交项目关联。"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models import (
    AuditLog,
    Organization,
    OrganizationSite,
    SalesProject,
    TypicalCase,
)
from app.services.account_access import AccountDataScope, location_condition
from app.typical_case_schemas import (
    MAINLAND_PROVINCE_ADCODES,
    TypicalCaseAdminListItem,
    TypicalCaseAdminOverview,
    TypicalCaseAdminRead,
    TypicalCaseImage,
    TypicalCaseInput,
    TypicalCaseMapRegion,
    TypicalCaseMapResponse,
    TypicalCaseMetric,
    TypicalCaseProjectOption,
    TypicalCasePublicDetail,
    TypicalCasePublicSummary,
)


def _case_query():
    """统一预加载成交项目与单位，避免列表序列化触发逐行查询。"""

    return select(TypicalCase).options(
        joinedload(TypicalCase.sales_project).joinedload(SalesProject.organization)
    )


def _images(case: TypicalCase) -> list[TypicalCaseImage]:
    """把数据库 JSONB 图片恢复为受校验的公开结构。"""

    return [TypicalCaseImage.model_validate(item) for item in case.images]


def _metrics(case: TypicalCase) -> list[TypicalCaseMetric]:
    """把数据库 JSONB 指标恢复为受校验的公开结构。"""

    return [TypicalCaseMetric.model_validate(item) for item in case.metrics]


def _cover_image(case: TypicalCase) -> TypicalCaseImage | None:
    """返回唯一封面；草稿没有封面时保持空值。"""

    return next((image for image in _images(case) if image.is_cover), None)


def _input_values(payload: TypicalCaseInput) -> dict[str, object]:
    """将嵌套 Pydantic 对象转换为 JSONB 可写的普通字典。"""

    values = payload.model_dump(exclude={"images", "metrics"})
    values["images"] = [item.model_dump() for item in payload.images]
    values["metrics"] = [item.model_dump() for item in payload.metrics]
    return values


def _public_summary(case: TypicalCase) -> TypicalCasePublicSummary:
    """裁剪案例为地图摘要，避免公开接口提前发送完整故事。"""

    return TypicalCasePublicSummary(
        id=case.id,
        province=case.province,
        province_adcode=case.province_adcode,
        city=case.city,
        title=case.title,
        subtitle=case.subtitle,
        customer_display_name=case.customer_display_name,
        industry_label=case.industry_label,
        summary=case.summary,
        cover_image=_cover_image(case),
        is_featured=case.is_featured,
    )


def to_admin_read(case: TypicalCase) -> TypicalCaseAdminRead:
    """返回管理端完整内容，并附带受保护的成交项目摘要。"""

    project = case.sales_project
    return TypicalCaseAdminRead(
        id=case.id,
        sales_project_id=case.sales_project_id,
        province=case.province,
        province_adcode=case.province_adcode,
        city=case.city,
        title=case.title,
        subtitle=case.subtitle,
        customer_display_name=case.customer_display_name,
        industry_label=case.industry_label,
        summary=case.summary,
        challenge=case.challenge,
        solution=case.solution,
        outcome=case.outcome,
        product_scope=case.product_scope,
        customer_quote=case.customer_quote,
        quote_attribution=case.quote_attribution,
        show_contract_amount=case.show_contract_amount,
        is_published=case.is_published,
        is_featured=case.is_featured,
        images=_images(case),
        metrics=_metrics(case),
        project_name=project.name if project is not None else None,
        organization_name=project.organization.name if project is not None else None,
        contract_amount=project.contract_amount if project is not None else None,
        signed_at=project.signed_at if project is not None else None,
        published_at=case.published_at,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


def list_public_typical_case_map(db: Session) -> TypicalCaseMapResponse:
    """匿名返回大陆 31 个省级区域，并在服务端计算上线与筹备数量。"""

    cases = list(db.scalars(
        _case_query()
        .where(TypicalCase.is_published.is_(True))
        .order_by(TypicalCase.is_featured.desc(), TypicalCase.province)
    ).all())
    cases_by_province = {case.province: case for case in cases}
    regions = [
        TypicalCaseMapRegion(
            province=province,
            province_adcode=adcode,
            status="已上线" if province in cases_by_province else "筹备中",
            case=_public_summary(cases_by_province[province]) if province in cases_by_province else None,
        )
        for province, adcode in MAINLAND_PROVINCE_ADCODES.items()
    ]
    return TypicalCaseMapResponse(
        total_regions=len(regions),
        published_count=len(cases),
        pending_count=len(regions) - len(cases),
        regions=regions,
    )


def get_public_typical_case(db: Session, case_id: UUID) -> TypicalCasePublicDetail:
    """匿名读取一条已发布案例，并按开关决定是否披露实际合同金额。"""

    case = db.scalar(_case_query().where(TypicalCase.id == case_id, TypicalCase.is_published.is_(True)))
    if case is None:
        raise HTTPException(status_code=404, detail="未找到已发布的典型案例")
    project = case.sales_project
    return TypicalCasePublicDetail(
        id=case.id,
        province=case.province,
        province_adcode=case.province_adcode,
        city=case.city,
        title=case.title,
        subtitle=case.subtitle,
        customer_display_name=case.customer_display_name,
        industry_label=case.industry_label,
        summary=case.summary,
        challenge=case.challenge,
        solution=case.solution,
        outcome=case.outcome,
        product_scope=case.product_scope,
        customer_quote=case.customer_quote,
        quote_attribution=case.quote_attribution,
        images=_images(case),
        metrics=_metrics(case),
        project_name=project.name if project is not None else None,
        signed_at=project.signed_at if project is not None else None,
        contract_amount=project.contract_amount if project is not None and case.show_contract_amount else None,
        published_at=case.published_at,
    )


def list_admin_typical_case_overview(db: Session) -> TypicalCaseAdminOverview:
    """合并真实案例与固定省份目录，让未配置省份也始终保留一个管理入口。"""

    cases = list(db.scalars(_case_query().order_by(TypicalCase.province)).all())
    cases_by_province = {case.province: case for case in cases}
    items: list[TypicalCaseAdminListItem] = []
    for province, adcode in MAINLAND_PROVINCE_ADCODES.items():
        case = cases_by_province.get(province)
        items.append(TypicalCaseAdminListItem(
            id=case.id if case else None,
            province=province,
            province_adcode=adcode,
            status="已上线" if case and case.is_published else "草稿" if case else "未配置",
            city=case.city if case else None,
            title=case.title if case else None,
            customer_display_name=case.customer_display_name if case else None,
            industry_label=case.industry_label if case else None,
            cover_image=_cover_image(case) if case else None,
            is_featured=case.is_featured if case else False,
            updated_at=case.updated_at if case else None,
        ))
    published_count = sum(case.is_published for case in cases)
    return TypicalCaseAdminOverview(
        total_regions=len(items),
        configured_count=len(cases),
        draft_count=len(cases) - published_count,
        published_count=published_count,
        items=items,
    )


def get_admin_typical_case(db: Session, case_id: UUID) -> TypicalCase:
    """读取管理端完整案例，未找到时返回统一中文错误。"""

    case = db.scalar(_case_query().where(TypicalCase.id == case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="未找到该典型案例")
    return case


def list_typical_case_project_options(
    db: Session,
    *,
    search: str | None,
    selected_id: UUID | None,
    province: str | None,
    data_scope: AccountDataScope | None = None,
) -> list[TypicalCaseProjectOption]:
    """最多搜索 40 个账号范围内同省成交项目，并确保授权已选项目可回显。"""

    base_statement = (
        select(
            SalesProject.id,
            SalesProject.name,
            Organization.name,
            OrganizationSite.province,
            OrganizationSite.city,
            SalesProject.contract_amount,
            SalesProject.signed_at,
        )
        .join(Organization, Organization.id == SalesProject.organization_id)
        .join(
            OrganizationSite,
            (OrganizationSite.organization_id == Organization.id) & OrganizationSite.is_primary.is_(True),
        )
        .where(OrganizationSite.province.is_not(None), OrganizationSite.city.is_not(None))
    )
    statement = base_statement
    if data_scope is not None:
        base_statement = base_statement.where(location_condition(OrganizationSite.province, OrganizationSite.city, data_scope))
        statement = base_statement
    if province:
        if province not in MAINLAND_PROVINCE_ADCODES:
            raise HTTPException(status_code=422, detail="请选择有效的大陆省级行政区")
        statement = statement.where(OrganizationSite.province == province)
    if search and search.strip():
        keyword = f"%{search.strip()}%"
        statement = statement.where(or_(
            SalesProject.name.ilike(keyword),
            Organization.name.ilike(keyword),
            OrganizationSite.province.ilike(keyword),
            OrganizationSite.city.ilike(keyword),
        ))
    rows = list(db.execute(statement.order_by(SalesProject.signed_at.desc().nullslast()).limit(40)).all())
    if selected_id is not None and all(row[0] != selected_id for row in rows):
        selected = db.execute(base_statement.where(SalesProject.id == selected_id)).one_or_none()
        if selected is not None:
            rows.append(selected)
    return [
        TypicalCaseProjectOption(
            id=row[0], project_name=row[1], organization_name=row[2], province=row[3], city=row[4],
            contract_amount=row[5], signed_at=row[6],
        )
        for row in rows
    ]


def _validate_project_location(db: Session, payload: TypicalCaseInput) -> None:
    """关联项目必须存在且主地点与案例省市一致，防止一省一案错配。"""

    if payload.sales_project_id is None:
        return
    row = db.execute(
        select(OrganizationSite.province, OrganizationSite.city)
        .join(Organization, Organization.id == OrganizationSite.organization_id)
        .join(SalesProject, SalesProject.organization_id == Organization.id)
        .where(SalesProject.id == payload.sales_project_id, OrganizationSite.is_primary.is_(True))
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=422, detail="关联成交项目不存在或所属单位缺少主地点")
    if row.province != payload.province or row.city != payload.city:
        raise HTTPException(status_code=422, detail="案例省市必须与关联成交项目的单位主地点一致")


def _commit_case(db: Session) -> None:
    """提交案例事务，并把约束冲突转换为不泄露 SQL 的中文错误。"""

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="该省份、成交项目或推荐位已有已发布案例") from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="典型案例保存失败，请稍后重试") from error


def _clear_other_featured(db: Session, case_id: UUID) -> None:
    """新推荐案例保存前取消旧推荐，保持全站唯一默认案例。"""

    db.execute(update(TypicalCase).where(TypicalCase.id != case_id, TypicalCase.is_featured.is_(True)).values(is_featured=False))


def create_typical_case(db: Session, payload: TypicalCaseInput, actor_username: str) -> TypicalCaseAdminRead:
    """原子新增典型案例并记录管理员审计。"""

    _validate_project_location(db, payload)
    case_id = uuid4()
    values = _input_values(payload)
    if payload.is_published:
        values["published_at"] = datetime.now(UTC)
    case = TypicalCase(id=case_id, **values)
    db.add(case)
    if payload.is_featured:
        _clear_other_featured(db, case_id)
    db.add(AuditLog(
        organization_id=None,
        actor_username=actor_username,
        action="新增典型案例",
        detail={"案例ID": str(case_id), "省份": payload.province, "是否发布": payload.is_published},
    ))
    _commit_case(db)
    return to_admin_read(get_admin_typical_case(db, case_id))


def update_typical_case(
    db: Session,
    case_id: UUID,
    payload: TypicalCaseInput,
    actor_username: str,
) -> TypicalCaseAdminRead:
    """原子覆盖案例内容，首次发布时由服务端记录发布时间。"""

    case = get_admin_typical_case(db, case_id)
    if payload.province != case.province or payload.province_adcode != case.province_adcode:
        raise HTTPException(status_code=422, detail="案例省份创建后不可修改，请返回省份列表重新选择")
    _validate_project_location(db, payload)
    values = _input_values(payload)
    if payload.is_published and not case.is_published:
        values["published_at"] = datetime.now(UTC)
    for field_name, value in values.items():
        setattr(case, field_name, value)
    if payload.is_featured:
        _clear_other_featured(db, case_id)
    db.add(AuditLog(
        organization_id=None,
        actor_username=actor_username,
        action="编辑典型案例",
        detail={"案例ID": str(case_id), "省份": payload.province, "是否发布": payload.is_published},
    ))
    _commit_case(db)
    return to_admin_read(get_admin_typical_case(db, case_id))


def delete_typical_case(db: Session, case_id: UUID, actor_username: str) -> None:
    """删除一条案例主档并保留独立审计记录。"""

    case = get_admin_typical_case(db, case_id)
    db.delete(case)
    db.add(AuditLog(
        organization_id=None,
        actor_username=actor_username,
        action="删除典型案例",
        detail={"案例ID": str(case_id), "省份": case.province, "标题": case.title},
    ))
    _commit_case(db)
