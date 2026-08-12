"""单位服务：集中处理筛选、证据约束、地址点位与审核操作，保持路由轻量。"""

import re
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from geoalchemy2.elements import WKTElement
from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import AuditLog, CustomerStatus, EvidenceKind, GeocodeStatus, Opportunity, Organization, OrganizationContact, OrganizationEvidence, OrganizationSite, OrganizationType, ReviewStatus, SalesProject
from app.schemas import OrganizationAdminCreate, OrganizationRead, OrganizationUpdate, ProvinceOrganizationSummary, ReviewAction, SiteInput
from app.services.geocoding import gcj02_to_wgs84


def normalize_name(name: str) -> str:
    """生成用于候选去重的名称键，保留原始名称供页面正常展示。"""

    return re.sub(r"[\s（）()\-—_]+", "", name).lower()


def _ensure_organization_is_not_duplicate(db: Session, name: str, *, exclude_id: UUID | None = None) -> None:
    """在管理员新增或改名前提示标准化同名记录，避免静默制造重复单位。"""

    statement = select(Organization).where(Organization.normalized_name == normalize_name(name))
    if exclude_id is not None:
        statement = statement.where(Organization.id != exclude_id)
    duplicate = db.scalar(statement.limit(1))
    if duplicate:
        raise HTTPException(status_code=409, detail=f"数据库中已存在同名单位“{duplicate.name}”，请核对后再添加")


def _query_with_relations() -> Select[tuple[Organization]]:
    """提供详情所需关联预加载，避免列表和抽屉发生 N+1 查询。"""

    return select(Organization).options(
        selectinload(Organization.sites),
        selectinload(Organization.evidences),
        selectinload(Organization.contacts),
        selectinload(Organization.opportunities),
        selectinload(Organization.sales_projects),
    )


def _site_from_input(site_input: object) -> OrganizationSite:
    """把地点输入转换成 ORM 对象，并将高德 GCJ-02 坐标转换后写入 PostGIS。"""

    values = site_input.model_dump()
    longitude = values.pop("longitude")
    latitude = values.pop("latitude")
    location = _postgis_location(longitude, latitude)
    return OrganizationSite(**values, longitude=longitude, latitude=latitude, location=location)


def _postgis_location(longitude: float | None, latitude: float | None) -> WKTElement | None:
    """把管理端/高德使用的 GCJ-02 坐标转换成 SRID 4326 的 WGS84 点位。"""

    if longitude is None or latitude is None:
        return None
    wgs_longitude, wgs_latitude = gcj02_to_wgs84(longitude, latitude)
    return WKTElement(f"POINT({wgs_longitude} {wgs_latitude})", srid=4326)


def create_organization(db: Session, payload: OrganizationAdminCreate, actor_username: str) -> Organization:
    """在一个事务内创建单位、主地点、证据和全部商业关联记录。"""

    _ensure_organization_is_not_duplicate(db, payload.name)
    site_input = SiteInput.model_validate({**payload.primary_site.model_dump(exclude_none=True), "is_primary": True})
    _validate_site_location(site_input.geocode_status, site_input.longitude, site_input.latitude)
    organization = Organization(
        name=payload.name.strip(),
        normalized_name=normalize_name(payload.name),
        organization_type=payload.organization_type,
        industry=payload.industry,
        customer_status=payload.customer_status,
        review_status=payload.review_status,
        inclusion_reason=payload.inclusion_reason,
        is_sports_exception=payload.is_sports_exception,
        parent_group=payload.parent_group,
        website=str(payload.website) if payload.website else None,
        unified_social_credit_code=payload.unified_social_credit_code,
        recent_follow_up_at=payload.recent_follow_up_at,
        recent_follow_up_content=payload.recent_follow_up_content,
        follow_up_owner=payload.follow_up_owner,
        cooperation_intent=payload.cooperation_intent,
        cooperation_level=payload.cooperation_level,
        notes=payload.notes,
        sites=[_site_from_input(site_input)],
        contacts=[OrganizationContact(**item.model_dump(exclude={"id"})) for item in payload.contacts],
        opportunities=[Opportunity(**item.model_dump(exclude={"id"})) for item in payload.opportunities],
        sales_projects=[SalesProject(**item.model_dump(exclude={"id"})) for item in payload.sales_projects],
        evidences=[
            OrganizationEvidence(
                evidence_kind=item.evidence_kind,
                title=item.title,
                source_url=str(item.source_url),
                published_at=item.published_at,
                excerpt=item.excerpt,
            )
            for item in payload.evidences
        ],
    )
    try:
        db.add(organization)
        db.flush()
        db.add(AuditLog(
            organization_id=organization.id,
            actor_username=actor_username,
            action="创建单位",
            detail={
                "联系人数量": len(payload.contacts),
                "成交项目数量": len(payload.sales_projects),
                "商机数量": len(payload.opportunities),
                "来源数量": len(payload.evidences),
            },
        ))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return get_organization(db, organization.id)


def get_organization(db: Session, organization_id: UUID) -> Organization:
    """读取一条完整单位档案；不存在时返回适合前端显示的中文 404。"""

    organization = db.scalar(_query_with_relations().where(Organization.id == organization_id))
    if not organization:
        raise HTTPException(status_code=404, detail="未找到该单位")
    return organization


def list_organizations(
    db: Session,
    *,
    page: int,
    page_size: int,
    search: str | None,
    types: Sequence[OrganizationType],
    customer_statuses: Sequence[CustomerStatus],
    review_statuses: Sequence[ReviewStatus],
    province: str | None,
    city: str | None,
    district: str | None,
    geocode_status: GeocodeStatus | None,
    sports_only: bool,
    verified_only: bool = False,
) -> tuple[list[Organization], int]:
    """按管理后台筛选项分页查询单位，地址条件只作用于关联地点。"""

    statement = _query_with_relations()
    count_statement = select(func.count(Organization.id)).select_from(Organization)
    conditions = _organization_filter_conditions(
        search=search, types=types, customer_statuses=customer_statuses, review_statuses=review_statuses,
        province=province, city=city, district=district, geocode_status=geocode_status,
        sports_only=sports_only, verified_only=verified_only,
    )
    if conditions:
        statement = statement.where(*conditions)
        count_statement = count_statement.where(*conditions)
    total = db.scalar(count_statement) or 0
    items = db.scalars(statement.order_by(Organization.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return list(items), total


def list_public_organizations(
    db: Session,
    *,
    page: int,
    page_size: int,
    search: str | None,
    types: Sequence[OrganizationType],
    customer_statuses: Sequence[CustomerStatus],
    review_statuses: Sequence[ReviewStatus],
    province: str | None,
    city: str | None,
    district: str | None,
) -> tuple[list[tuple[Organization, int]], int]:
    """分页读取公开目录需要的主档、地点和证据计数，不加载内部商业关联。"""

    evidence_counts = (
        select(
            OrganizationEvidence.organization_id.label("organization_id"),
            func.count(OrganizationEvidence.id).label("evidence_count"),
        )
        .group_by(OrganizationEvidence.organization_id)
        .subquery()
    )
    conditions = _organization_filter_conditions(
        search=search,
        types=types,
        customer_statuses=customer_statuses,
        review_statuses=review_statuses,
        province=province,
        city=city,
        district=district,
        geocode_status=None,
        sports_only=False,
        verified_only=False,
    )
    statement = (
        select(Organization, func.coalesce(evidence_counts.c.evidence_count, 0))
        .outerjoin(evidence_counts, evidence_counts.c.organization_id == Organization.id)
        .options(selectinload(Organization.sites))
    )
    count_statement = select(func.count(Organization.id)).select_from(Organization)
    if conditions:
        statement = statement.where(*conditions)
        count_statement = count_statement.where(*conditions)
    total = db.scalar(count_statement) or 0
    rows = db.execute(
        statement.order_by(Organization.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return [(organization, int(evidence_count)) for organization, evidence_count in rows], total


def summarize_organizations_by_province(db: Session) -> list[ProvinceOrganizationSummary]:
    """按主地点聚合省份单位总量、单位类型和客户状态，供公开热力图一次读取。"""

    rows = db.execute(
        select(
            OrganizationSite.province,
            Organization.organization_type,
            Organization.customer_status,
            func.count(func.distinct(Organization.id)),
        )
        .select_from(Organization)
        .join(OrganizationSite, OrganizationSite.organization_id == Organization.id)
        .where(OrganizationSite.is_primary.is_(True), OrganizationSite.province.is_not(None))
        .group_by(OrganizationSite.province, Organization.organization_type, Organization.customer_status)
    ).all()
    summaries: dict[str, ProvinceOrganizationSummary] = {}
    for province, organization_type, customer_status, count in rows:
        summary = summaries.setdefault(
            province,
            ProvinceOrganizationSummary(province=province, total=0, organization_types={}, customer_statuses={}),
        )
        summary.total += count
        summary.organization_types[organization_type.value] = summary.organization_types.get(organization_type.value, 0) + count
        summary.customer_statuses[customer_status.value] = summary.customer_statuses.get(customer_status.value, 0) + count
    return sorted(summaries.values(), key=lambda item: (-item.total, item.province))


def list_organizations_for_export(
    db: Session,
    *,
    search: str | None,
    types: Sequence[OrganizationType],
    customer_statuses: Sequence[CustomerStatus],
    review_statuses: Sequence[ReviewStatus],
    province: str | None,
    city: str | None,
    district: str | None,
    geocode_status: GeocodeStatus | None,
    sports_only: bool,
    verified_only: bool,
) -> list[Organization]:
    """导出时复用列表筛选条件读取全部匹配单位，避免浏览器分页导致下载缺行。"""

    statement = _query_with_relations()
    conditions = _organization_filter_conditions(
        search=search, types=types, customer_statuses=customer_statuses, review_statuses=review_statuses,
        province=province, city=city, district=district, geocode_status=geocode_status,
        sports_only=sports_only, verified_only=verified_only,
    )
    if conditions:
        statement = statement.where(*conditions)
    return list(db.scalars(statement.order_by(Organization.name)).unique().all())


def _organization_filter_conditions(
    *,
    search: str | None,
    types: Sequence[OrganizationType],
    customer_statuses: Sequence[CustomerStatus],
    review_statuses: Sequence[ReviewStatus],
    province: str | None,
    city: str | None,
    district: str | None,
    geocode_status: GeocodeStatus | None,
    sports_only: bool,
    verified_only: bool,
) -> list[object]:
    """集中维护列表与导出共享的筛选语义，防止同一条件在不同入口结果不一致。"""

    conditions: list[object] = []
    site_conditions: list[object] = []
    if search:
        conditions.append(Organization.name.ilike(f"%{search.strip()}%"))
    if types:
        conditions.append(Organization.organization_type.in_(types))
    if customer_statuses:
        conditions.append(Organization.customer_status.in_(customer_statuses))
    if review_statuses:
        conditions.append(Organization.review_status.in_(review_statuses))
    if province:
        site_conditions.append(OrganizationSite.province == province)
    if city:
        site_conditions.append(OrganizationSite.city == city)
    if district:
        site_conditions.append(OrganizationSite.district == district)
    if geocode_status:
        site_conditions.append(OrganizationSite.geocode_status == geocode_status)
    if sports_only:
        conditions.append(Organization.is_sports_exception.is_(True))
    if verified_only:
        conditions.append(Organization.review_status == ReviewStatus.verified)
        site_conditions.append(OrganizationSite.geocode_status == GeocodeStatus.resolved)
    if site_conditions:
        # EXISTS 保证一个单位只占一个分页槽位，同时要求省/市/区条件命中同一地点。
        conditions.append(Organization.sites.any(and_(*site_conditions)))
    return conditions


def _validate_site_location(geocode_status: GeocodeStatus, longitude: float | None, latitude: float | None) -> None:
    """保护地图数据完整性：经纬度必须成对，已定位地点必须具有完整坐标。"""

    if (longitude is None) != (latitude is None):
        raise HTTPException(status_code=422, detail="经度和纬度必须同时填写或同时留空")
    if geocode_status is GeocodeStatus.resolved and longitude is None:
        raise HTTPException(status_code=422, detail="已定位地点必须填写经度和纬度")


def _update_primary_site(organization: Organization, changes: dict[str, object]) -> None:
    """更新现有主地点或为尚无地点的单位创建主地点，并同步空间点。"""

    site = next((item for item in organization.sites if item.is_primary), organization.sites[0] if organization.sites else None)
    if site is None:
        site_values = {**changes, "geocode_status": changes.get("geocode_status") or GeocodeStatus.pending, "is_primary": True}
        site_input = SiteInput.model_validate(site_values)
        _validate_site_location(site_input.geocode_status, site_input.longitude, site_input.latitude)
        organization.sites.append(_site_from_input(site_input))
        return

    longitude = changes.get("longitude", site.longitude)
    latitude = changes.get("latitude", site.latitude)
    geocode_status = changes.get("geocode_status") or site.geocode_status
    assert isinstance(geocode_status, GeocodeStatus)
    assert longitude is None or isinstance(longitude, (int, float))
    assert latitude is None or isinstance(latitude, (int, float))
    _validate_site_location(geocode_status, longitude, latitude)
    for field, value in changes.items():
        setattr(site, field, value)
    if "longitude" in changes or "latitude" in changes:
        site.location = _postgis_location(longitude, latitude)


def _sync_related_records(db: Session, records: list[Any], payloads: list[Any], model_class: type[Any], label: str) -> None:
    """按子记录 ID 同步一对多集合；缺失 ID 新增，未提交的旧记录删除。"""

    existing = {record.id: record for record in records}
    retained_ids: set[UUID] = set()
    for payload in payloads:
        values = payload.model_dump(exclude={"id"})
        if payload.id is None:
            records.append(model_class(**values))
            continue
        record = existing.get(payload.id)
        if record is None:
            raise HTTPException(status_code=422, detail=f"{label}记录不属于当前单位")
        retained_ids.add(payload.id)
        for field, value in values.items():
            setattr(record, field, value)
    for record_id, record in existing.items():
        if record_id not in retained_ids:
            db.delete(record)


def update_organization(db: Session, organization_id: UUID, payload: OrganizationUpdate, actor_username: str) -> Organization:
    """原子更新单位主档、主地点及联系人、成交项目和商机集合。"""

    organization = get_organization(db, organization_id)
    changes = payload.model_dump(exclude_unset=True)
    site_changes = changes.pop("primary_site", None)
    contact_changes = changes.pop("contacts", None)
    sales_project_changes = changes.pop("sales_projects", None)
    opportunity_changes = changes.pop("opportunities", None)
    resulting_type = changes.get("organization_type", organization.organization_type)
    resulting_sports_exception = changes.get("is_sports_exception", organization.is_sports_exception)
    if resulting_sports_exception and resulting_type is not OrganizationType.university:
        raise HTTPException(status_code=422, detail="体育例外仅适用于高校类型")
    if "name" in changes and changes["name"] is not None:
        _ensure_organization_is_not_duplicate(db, str(changes["name"]), exclude_id=organization.id)
    for field, value in changes.items():
        if field == "website" and value is not None:
            value = str(value)
        if field == "name" and value is not None:
            value = value.strip()
            organization.normalized_name = normalize_name(value)
        setattr(organization, field, value)
    if site_changes is not None:
        _update_primary_site(organization, site_changes)
    if contact_changes is not None:
        _sync_related_records(db, organization.contacts, payload.contacts or [], OrganizationContact, "联系人")
    if opportunity_changes is not None:
        _sync_related_records(db, organization.opportunities, payload.opportunities or [], Opportunity, "商机")
    retained_opportunity_ids = {
        item.id for item in (payload.opportunities if opportunity_changes is not None else organization.opportunities) if item.id is not None
    }
    if sales_project_changes is not None:
        for project in payload.sales_projects or []:
            if project.opportunity_id is not None and project.opportunity_id not in retained_opportunity_ids:
                raise HTTPException(status_code=422, detail="成交项目关联商机必须属于当前单位")
        _sync_related_records(db, organization.sales_projects, payload.sales_projects or [], SalesProject, "成交项目")
    audit_fields = [
        *changes,
        *(["primary_site"] if site_changes is not None else []),
        *(["contacts"] if contact_changes is not None else []),
        *(["sales_projects"] if sales_project_changes is not None else []),
        *(["opportunities"] if opportunity_changes is not None else []),
    ]
    db.add(AuditLog(organization_id=organization.id, actor_username=actor_username, action="编辑单位", detail={"字段": audit_fields}))
    db.commit()
    return get_organization(db, organization_id)


def delete_organization(db: Session, organization_id: UUID, actor_username: str) -> None:
    """永久删除管理员确认的单位及其级联子记录，并保留脱敏删除审计。"""

    organization = get_organization(db, organization_id)
    deleted_detail = {"单位ID": str(organization.id), "单位名称": organization.name}
    db.delete(organization)
    db.flush()
    db.add(AuditLog(organization_id=None, actor_username=actor_username, action="删除单位", detail=deleted_detail))
    db.commit()


def review_organization(db: Session, organization_id: UUID, payload: ReviewAction, actor_username: str) -> Organization:
    """执行核验或排除操作；排除理由写入审核日志而不删除原始记录。"""

    organization = get_organization(db, organization_id)
    organization.review_status = payload.review_status
    db.add(AuditLog(organization_id=organization.id, actor_username=actor_username, action="审核单位", detail={"状态": payload.review_status.value, "备注": payload.note}))
    db.commit()
    return get_organization(db, organization_id)


def to_read(organization: Organization) -> OrganizationRead:
    """从加载完整的 ORM 档案生成稳定的 API 响应。"""

    return OrganizationRead.model_validate(organization)
