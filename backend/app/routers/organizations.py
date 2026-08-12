"""单位目录路由：复用查询逻辑提供公开读取，并保护审核、写入和导出 API。"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CustomerStatus, GeocodeStatus, Organization, OrganizationSite, OrganizationType, ReviewStatus
from app.schemas import FilterOptions, MapPoint, OrganizationAdminCreate, OrganizationPage, OrganizationRead, OrganizationUpdate, ProvinceOrganizationSummary, PublicOrganizationPage, PublicOrganizationRead, PublicSiteRead, ReviewAction
from app.services.auth import get_current_admin
from app.services.organization_exports import build_organization_export_workbook
from app.services.organizations import create_organization, delete_organization, get_organization, list_organizations, list_organizations_for_export, list_public_organizations, review_organization, summarize_organizations_by_province, to_read, update_organization

router = APIRouter(prefix="/organizations", tags=["单位管理"])
public_router = APIRouter(prefix="/public/organizations", tags=["公开单位目录"])


@router.get("/filters", response_model=FilterOptions, dependencies=[Depends(get_current_admin)])
@public_router.get("/filters", response_model=FilterOptions)
def filter_options(
    province: str | None = Query(default=None, max_length=60),
    city: str | None = Query(default=None, max_length=60),
    db: Session = Depends(get_db),
) -> FilterOptions:
    """按已选省市返回完整层级选项，供地图和单位库共享同一数据库口径。"""

    provinces = db.scalars(select(distinct(OrganizationSite.province)).where(OrganizationSite.province.is_not(None)).order_by(OrganizationSite.province)).all()
    city_statement = select(distinct(OrganizationSite.city)).where(OrganizationSite.city.is_not(None))
    if province:
        city_statement = city_statement.where(OrganizationSite.province == province)
    cities = db.scalars(city_statement.order_by(OrganizationSite.city)).all() if province else []
    district_statement = select(distinct(OrganizationSite.district)).where(OrganizationSite.district.is_not(None))
    if province and city:
        district_statement = district_statement.where(OrganizationSite.province == province, OrganizationSite.city == city)
    districts = db.scalars(district_statement.order_by(OrganizationSite.district)).all() if province and city else []
    return FilterOptions(
        organization_types=[item.value for item in OrganizationType],
        customer_statuses=[item.value for item in CustomerStatus],
        review_statuses=[item.value for item in ReviewStatus],
        provinces=list(provinces),
        cities=list(cities),
        districts=list(districts),
    )


@public_router.get("/province-summaries", response_model=list[ProvinceOrganizationSummary])
def province_summaries(db: Session = Depends(get_db)) -> list[ProvinceOrganizationSummary]:
    """匿名返回省级单位聚合数据，不暴露单位明细、地址或坐标。"""

    return summarize_organizations_by_province(db)


@router.get("/map-points", response_model=list[MapPoint], dependencies=[Depends(get_current_admin)])
@public_router.get("/map-points", response_model=list[MapPoint])
def map_points(
    types: list[OrganizationType] = Query(default=[]),
    customer_statuses: list[CustomerStatus] = Query(default=[]),
    review_statuses: list[ReviewStatus] = Query(default=[]),
    province: str | None = None,
    city: str | None = Query(default=None, max_length=60),
    district: str | None = Query(default=None, max_length=80),
    verified_only: bool = False,
    db: Session = Depends(get_db),
) -> list[MapPoint]:
    """只返回有可靠坐标的主地点，交由前端 AMap.MarkerCluster 在视图范围内聚合。"""

    statement = select(Organization, OrganizationSite).join(OrganizationSite).where(
        OrganizationSite.is_primary.is_(True),
        OrganizationSite.geocode_status == GeocodeStatus.resolved,
        OrganizationSite.longitude.is_not(None),
        OrganizationSite.latitude.is_not(None),
    )
    if types:
        statement = statement.where(Organization.organization_type.in_(types))
    if customer_statuses:
        statement = statement.where(Organization.customer_status.in_(customer_statuses))
    if review_statuses:
        statement = statement.where(Organization.review_status.in_(review_statuses))
    if province:
        statement = statement.where(OrganizationSite.province == province)
    if city:
        statement = statement.where(OrganizationSite.city == city)
    if district:
        statement = statement.where(OrganizationSite.district == district)
    if verified_only:
        statement = statement.where(Organization.review_status == ReviewStatus.verified)
    rows = db.execute(statement.limit(25000)).all()
    return [
        MapPoint(
            id=organization.id,
            name=organization.name,
            organization_type=organization.organization_type,
            customer_status=organization.customer_status,
            review_status=organization.review_status,
            longitude=site.longitude,
            latitude=site.latitude,
            province=site.province,
            city=site.city,
            district=site.district,
        )
        for organization, site in rows
    ]


@router.get("", response_model=OrganizationPage, dependencies=[Depends(get_current_admin)])
def organizations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    search: str | None = None,
    types: list[OrganizationType] = Query(default=[]),
    customer_statuses: list[CustomerStatus] = Query(default=[]),
    review_statuses: list[ReviewStatus] = Query(default=[]),
    province: str | None = None,
    city: str | None = None,
    district: str | None = None,
    geocode_status: GeocodeStatus | None = None,
    sports_only: bool = False,
    verified_only: bool = False,
    db: Session = Depends(get_db),
) -> OrganizationPage:
    """返回可核查的分页单位列表，避免二万条候选记录拖慢审核页面。"""

    items, total = list_organizations(
        db,
        page=page,
        page_size=page_size,
        search=search,
        types=types,
        customer_statuses=customer_statuses,
        review_statuses=review_statuses,
        province=province,
        city=city,
        district=district,
        geocode_status=geocode_status,
        sports_only=sports_only,
        verified_only=verified_only,
    )
    return OrganizationPage(items=[to_read(item) for item in items], total=total, page=page, page_size=page_size)


@public_router.get("", response_model=PublicOrganizationPage)
def public_organizations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    search: str | None = None,
    types: list[OrganizationType] = Query(default=[]),
    customer_statuses: list[CustomerStatus] = Query(default=[]),
    review_statuses: list[ReviewStatus] = Query(default=[]),
    province: str | None = None,
    city: str | None = None,
    district: str | None = None,
    db: Session = Depends(get_db),
) -> PublicOrganizationPage:
    """匿名返回主站正在展示的单位字段，排除详细地址、备注和证据内容。"""

    rows, total = list_public_organizations(
        db,
        page=page,
        page_size=page_size,
        search=search,
        types=types,
        customer_statuses=customer_statuses,
        review_statuses=review_statuses,
        province=province,
        city=city,
        district=district,
    )
    public_items = [
        PublicOrganizationRead(
            id=item.id,
            name=item.name,
            organization_type=item.organization_type,
            industry=item.industry,
            customer_status=item.customer_status,
            review_status=item.review_status,
            inclusion_reason=item.inclusion_reason,
            is_sports_exception=item.is_sports_exception,
            parent_group=item.parent_group,
            website=item.website,
            recent_follow_up_at=item.recent_follow_up_at,
            recent_follow_up_content=item.recent_follow_up_content,
            cooperation_intent=item.cooperation_intent,
            cooperation_level=item.cooperation_level,
            evidence_count=evidence_count,
            sites=[PublicSiteRead.model_validate(site) for site in item.sites],
        )
        for item, evidence_count in rows
    ]
    return PublicOrganizationPage(items=public_items, total=total, page=page, page_size=page_size)


@router.get("/export")
def export_organizations(
    search: str | None = None,
    types: list[OrganizationType] = Query(default=[]),
    customer_statuses: list[CustomerStatus] = Query(default=[]),
    review_statuses: list[ReviewStatus] = Query(default=[]),
    province: str | None = None,
    city: str | None = None,
    district: str | None = None,
    geocode_status: GeocodeStatus | None = None,
    sports_only: bool = False,
    verified_only: bool = False,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
) -> StreamingResponse:
    """下载与当前审核列表同条件的 Excel，避免人工翻页或另行拼接候选数据。"""

    organizations = list_organizations_for_export(
        db, search=search, types=types, customer_statuses=customer_statuses, review_statuses=review_statuses,
        province=province, city=city, district=district, geocode_status=geocode_status, sports_only=sports_only,
        verified_only=verified_only,
    )
    workbook = build_organization_export_workbook(organizations)
    return StreamingResponse(
        iter([workbook]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="unite-organizations.xlsx"'},
    )


@router.post("", response_model=OrganizationRead, status_code=201)
def create(payload: OrganizationAdminCreate, db: Session = Depends(get_db), user=Depends(get_current_admin)) -> OrganizationRead:
    """管理员原子写入单位主档、主地点和可选关联记录。"""

    return to_read(create_organization(db, payload, user.username))


@router.get("/{organization_id}", response_model=OrganizationRead)
def detail(organization_id: UUID, db: Session = Depends(get_db), _user=Depends(get_current_admin)) -> OrganizationRead:
    """提供列表抽屉与地图 pin 详情所需的单条单位档案。"""

    return to_read(get_organization(db, organization_id))


@router.patch("/{organization_id}", response_model=OrganizationRead)
def update(organization_id: UUID, payload: OrganizationUpdate, db: Session = Depends(get_db), user=Depends(get_current_admin)) -> OrganizationRead:
    """保存审核人员对单位主档案的人工修正，并自动记录操作日志。"""

    return to_read(update_organization(db, organization_id, payload, user.username))


@router.delete("/{organization_id}", status_code=204)
def delete(organization_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_admin)) -> Response:
    """仅在管理员二次确认后永久删除单位，数据库级联清理关联子记录。"""

    delete_organization(db, organization_id, user.username)
    return Response(status_code=204)


@router.post("/{organization_id}/review", response_model=OrganizationRead)
def review(organization_id: UUID, payload: ReviewAction, db: Session = Depends(get_db), user=Depends(get_current_admin)) -> OrganizationRead:
    """标记已核验或不纳入，保留原始记录和排除理由供后续复核。"""

    return to_read(review_organization(db, organization_id, payload, user.username))
