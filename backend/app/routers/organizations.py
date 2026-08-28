"""单位目录路由：复用查询逻辑提供公开读取，并保护审核、写入和导出 API。"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    CustomerStatus,
    GeocodeStatus,
    AdminUser,
    Organization,
    OrganizationSite,
    OrganizationType,
    ReviewStatus,
    Salesperson,
)
from app.schemas import (
    FilterOptions,
    MapPoint,
    OrganizationAdminCreate,
    OrganizationBatchAction,
    OrganizationBatchResult,
    OrganizationPage,
    OrganizationRead,
    OrganizationUpdate,
    PublicOrganizationPage,
    PublicOrganizationRead,
    PublicSiteRead,
    PublicWonCustomerMapPointRead,
    ReviewAction,
    SalespersonOptionRead,
)
from app.services.account_access import (
    account_data_scope,
    location_condition,
    location_is_visible,
    require_location_access,
    require_organization_access,
)
from app.services.auth import get_current_admin, get_current_user
from app.services.competitors import public_organization_competitor_links
from app.services.organization_exports import build_organization_export_workbook
from app.services.organizations import (
    batch_update_organizations,
    create_organization,
    delete_organization,
    get_organization,
    list_organization_map_points,
    list_organizations,
    list_organizations_for_export,
    list_public_organizations,
    list_public_won_customer_map_points,
    review_organization,
    to_read,
    update_organization,
)

router = APIRouter(prefix="/organizations", tags=["单位管理"])
public_router = APIRouter(prefix="/public/organizations", tags=["公开单位目录"])


@router.get("/filters", response_model=FilterOptions, dependencies=[Depends(get_current_admin)])
@public_router.get("/filters", response_model=FilterOptions)
def filter_options(
    province: str | None = Query(default=None, max_length=60),
    city: str | None = Query(default=None, max_length=60),
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
) -> FilterOptions:
    """返回账号范围内地点层级与销售人员选项，管理员仍保持全国范围。"""

    data_scope = account_data_scope(user)
    scope_condition = location_condition(OrganizationSite.province, OrganizationSite.city, data_scope)
    provinces = db.scalars(select(distinct(OrganizationSite.province)).join(Organization).where(OrganizationSite.province.is_not(None), Organization.archived_at.is_(None), scope_condition).order_by(OrganizationSite.province)).all()
    city_statement = select(distinct(OrganizationSite.city)).join(Organization).where(OrganizationSite.city.is_not(None), Organization.archived_at.is_(None), scope_condition)
    if province:
        city_statement = city_statement.where(OrganizationSite.province == province)
    cities = db.scalars(city_statement.order_by(OrganizationSite.city)).all() if province else []
    district_statement = select(distinct(OrganizationSite.district)).join(Organization).where(OrganizationSite.district.is_not(None), Organization.archived_at.is_(None), scope_condition)
    if province and city:
        district_statement = district_statement.where(OrganizationSite.province == province, OrganizationSite.city == city)
    districts = db.scalars(district_statement.order_by(OrganizationSite.district)).all() if province and city else []
    salespeople = db.scalars(select(Salesperson).order_by(Salesperson.is_active.desc(), Salesperson.employee_code, Salesperson.id)).all()
    return FilterOptions(
        organization_types=[item.value for item in OrganizationType],
        customer_statuses=[item.value for item in CustomerStatus],
        review_statuses=[item.value for item in ReviewStatus],
        provinces=list(provinces),
        cities=list(cities),
        districts=list(districts),
        salespeople=[SalespersonOptionRead.model_validate(item) for item in salespeople],
    )


@public_router.get("/won-customers", response_model=list[PublicWonCustomerMapPointRead])
def public_won_customers(db: Session = Depends(get_db)) -> list[PublicWonCustomerMapPointRead]:
    """匿名返回已成交且具备可靠主地点的优纳特客户及实际成交项目。"""

    return list_public_won_customer_map_points(db)


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
    user: AdminUser = Depends(get_current_user),
) -> list[MapPoint]:
    """返回账号范围内可信主地点与安全商机汇总，管理员仍读取全国。"""

    return list_organization_map_points(
        db,
        types=types,
        customer_statuses=customer_statuses,
        review_statuses=review_statuses,
        province=province,
        city=city,
        district=district,
        verified_only=verified_only,
        data_scope=account_data_scope(user),
    )


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
    archived_only: bool = False,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_admin),
) -> OrganizationPage:
    """返回账号范围内可核查的分页单位列表，避免跨区域读取和全量加载。"""

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
        archived_only=archived_only,
        data_scope=account_data_scope(user),
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
    user: AdminUser = Depends(get_current_user),
) -> PublicOrganizationPage:
    """返回账号范围内主站单位字段，排除详细地址、备注和证据内容。"""

    data_scope = account_data_scope(user)

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
        data_scope=data_scope,
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
            sites=[
                PublicSiteRead.model_validate(site)
                for site in item.sites
                if location_is_visible(data_scope, site.province, site.city)
            ],
            competitor_contracts=public_organization_competitor_links(item),
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
    user: AdminUser = Depends(get_current_admin),
) -> StreamingResponse:
    """下载当前账号范围与筛选条件共同命中的单位，防止导出绕过页面权限。"""

    organizations = list_organizations_for_export(
        db, search=search, types=types, customer_statuses=customer_statuses, review_statuses=review_statuses,
        province=province, city=city, district=district, geocode_status=geocode_status, sports_only=sports_only,
        verified_only=verified_only,
        data_scope=account_data_scope(user),
    )
    workbook = build_organization_export_workbook(organizations)
    return StreamingResponse(
        iter([workbook]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="unite-organizations.xlsx"'},
    )


@router.post("", response_model=OrganizationRead, status_code=201)
def create(payload: OrganizationAdminCreate, db: Session = Depends(get_db), user=Depends(get_current_admin)) -> OrganizationRead:
    """在账号负责区域内原子写入单位主档、主地点和可选关联记录。"""

    require_location_access(account_data_scope(user), payload.primary_site.province, payload.primary_site.city)
    return to_read(create_organization(db, payload, user.username))


@router.post("/batch", response_model=OrganizationBatchResult)
def batch_update(payload: OrganizationBatchAction, db: Session = Depends(get_db), user=Depends(get_current_admin)) -> OrganizationBatchResult:
    """确认全部所选单位都在账号范围内，再以单一事务处理批量动作。"""

    data_scope = account_data_scope(user)
    for organization_id in payload.ids:
        require_organization_access(db, organization_id, data_scope)
    return OrganizationBatchResult(updated=batch_update_organizations(db, payload, user.username))


@router.get("/{organization_id}", response_model=OrganizationRead)
def detail(organization_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_admin)) -> OrganizationRead:
    """只提供账号范围内列表抽屉与地图 pin 所需的完整单位档案。"""

    require_organization_access(db, organization_id, account_data_scope(user))
    return to_read(get_organization(db, organization_id))


@router.patch("/{organization_id}", response_model=OrganizationRead)
def update(organization_id: UUID, payload: OrganizationUpdate, db: Session = Depends(get_db), user=Depends(get_current_admin)) -> OrganizationRead:
    """保存账号范围内单位的人工修正，并自动记录操作日志。"""

    require_organization_access(db, organization_id, account_data_scope(user))
    return to_read(update_organization(db, organization_id, payload, user.username))


@router.delete("/{organization_id}", status_code=204)
def delete(organization_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_admin)) -> Response:
    """仅在区域权限和二次确认均通过后永久删除单位。"""

    require_organization_access(db, organization_id, account_data_scope(user))
    delete_organization(db, organization_id, user.username)
    return Response(status_code=204)


@router.post("/{organization_id}/review", response_model=OrganizationRead)
def review(organization_id: UUID, payload: ReviewAction, db: Session = Depends(get_db), user=Depends(get_current_admin)) -> OrganizationRead:
    """在账号范围内标记已核验或不纳入，并保留排除理由。"""

    require_organization_access(db, organization_id, account_data_scope(user))
    return to_read(review_organization(db, organization_id, payload, user.username))
