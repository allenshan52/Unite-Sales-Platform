"""账号区域权限服务：把市、省、大区和全国范围转换为可复用的 SQL 地点条件。"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import String, and_, cast, exists, false, or_, select, true
from sqlalchemy.orm import Session

from fastapi import HTTPException, status

from app.models import (
    AdminUser,
    AuditLog,
    Competitor,
    CompetitorCustomer,
    CompetitorDeal,
    CompetitorSite,
    CustomerGroup,
    CustomerGroupUnit,
    Organization,
    OrganizationSite,
    SalesProject,
    UserRole,
)
from app.sales_coverage import SALES_PROVINCES, SALES_REGION_PROVINCES, SalesCoverageLevel, canonical_province


_FULL_PROVINCE_NAMES = {
    "北京": "北京市", "天津": "天津市", "上海": "上海市", "重庆": "重庆市",
    "内蒙古": "内蒙古自治区", "广西": "广西壮族自治区", "西藏": "西藏自治区",
    "宁夏": "宁夏回族自治区", "新疆": "新疆维吾尔自治区",
}


@dataclass(frozen=True)
class AccountDataScope:
    """保存账号一次请求内的规范化可见范围，避免各服务重复解释权限。"""

    unrestricted: bool
    provinces: frozenset[str]
    cities: frozenset[tuple[str, str]]
    regions: frozenset[str]

    @property
    def visible_provinces(self) -> frozenset[str]:
        """返回地图可展示的省份；市级范围只贡献其所属省份。"""

        return self.provinces | frozenset(province for province, _city in self.cities)


def province_storage_names(province: str) -> tuple[str, ...]:
    """返回业务短名及数据库可能保存的行政区全称。"""

    canonical = canonical_province(province) or province
    full = _FULL_PROVINCE_NAMES.get(canonical, f"{canonical}省")
    return (canonical, full) if canonical != full else (canonical,)


def region_for_province(province: str) -> str | None:
    """按固定销售大区口径反查一个省份所属大区。"""

    canonical = canonical_province(province)
    return next((name for name, provinces in SALES_REGION_PROVINCES.items() if canonical in provinces), None)


def account_data_scope(user: AdminUser, *, expand_regions: bool = False) -> AccountDataScope:
    """把账号范围合并为地点权限；大区视角会把任一命中省市扩展到完整大区。"""

    scopes = list(getattr(user, "coverage_scopes", ()))
    unrestricted = getattr(user, "role", UserRole.admin) == UserRole.admin or any(scope.scope_level == SalesCoverageLevel.national for scope in scopes)
    if unrestricted:
        return AccountDataScope(True, frozenset(SALES_PROVINCES), frozenset(), frozenset(SALES_REGION_PROVINCES))

    provinces: set[str] = set()
    cities: set[tuple[str, str]] = set()
    regions: set[str] = set()
    for scope in scopes:
        if scope.scope_level == SalesCoverageLevel.region:
            regions.add(scope.scope_name)
            provinces.update(SALES_REGION_PROVINCES.get(scope.scope_name, ()))
        elif scope.scope_level == SalesCoverageLevel.province:
            if province := canonical_province(scope.province or scope.scope_name):
                provinces.add(province)
        elif scope.scope_level == SalesCoverageLevel.city:
            if (province := canonical_province(scope.province)) and scope.city:
                cities.add((province, scope.city))

    if expand_regions:
        regions.update(filter(None, (region_for_province(province) for province in provinces)))
        regions.update(filter(None, (region_for_province(province) for province, _city in cities)))
        provinces = {province for region in regions for province in SALES_REGION_PROVINCES[region]}
        cities.clear()
    return AccountDataScope(False, frozenset(provinces), frozenset(cities), frozenset(regions))


def location_condition(province_column, city_column, scope: AccountDataScope):
    """生成命中任一负责省或市的 SQL 条件；全国账号直接返回真条件。"""

    if scope.unrestricted:
        return true()
    conditions = [province_column.in_(province_storage_names(province)) for province in scope.provinces]
    conditions.extend(
        and_(province_column.in_(province_storage_names(province)), city_column == city)
        for province, city in scope.cities
    )
    return or_(*conditions) if conditions else false()


def location_is_visible(scope: AccountDataScope, province: str | None, city: str | None) -> bool:
    """在响应组装阶段复用同一地点口径，防止加载后的关联地点绕过 SQL 范围。"""

    if scope.unrestricted:
        return True
    canonical = canonical_province(province)
    if canonical is None:
        return False
    return canonical in scope.provinces or (city is not None and (canonical, city) in scope.cities)


def require_location_access(scope: AccountDataScope, province: str | None, city: str | None) -> None:
    """拒绝写入账号范围外的单地点记录，避免只靠前端筛选保护业务数据。"""

    if not location_is_visible(scope, province, city):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号不能修改该区域的数据")


def coverage_scope_is_visible(
    scope: AccountDataScope,
    scope_level: SalesCoverageLevel,
    scope_name: str,
    province: str | None,
    city: str | None,
) -> bool:
    """判断销售人员的一条市、省、大区或全国覆盖是否与账号负责区域相交。"""

    if scope.unrestricted:
        return True
    if scope_level == SalesCoverageLevel.national:
        return False
    if scope_level == SalesCoverageLevel.region:
        return any(item in scope.visible_provinces for item in SALES_REGION_PROVINCES.get(scope_name, ()))
    if scope_level == SalesCoverageLevel.province:
        return canonical_province(province or scope_name) in scope.visible_provinces
    return location_is_visible(scope, province, city)


def organization_visibility_condition(scope: AccountDataScope):
    """单位任一地点命中账号范围即可读取和维护整个跨省单位档案。"""

    if scope.unrestricted:
        return true()
    return exists(select(1).where(
        OrganizationSite.organization_id == Organization.id,
        location_condition(OrganizationSite.province, OrganizationSite.city, scope),
    ))


def customer_group_visibility_condition(scope: AccountDataScope):
    """客户集团任一总部或分支命中账号范围即可维护完整跨省集团。"""

    if scope.unrestricted:
        return true()
    return exists(select(1).where(
        CustomerGroupUnit.group_id == CustomerGroup.id,
        location_condition(CustomerGroupUnit.province, CustomerGroupUnit.city, scope),
    ))


def unite_deal_visibility_condition(scope: AccountDataScope):
    """优纳特订单优先按完整所在地快照授权；仅旧订单缺失快照时回退单位地点。"""

    if scope.unrestricted:
        return true()
    has_snapshot = and_(SalesProject.province.is_not(None), SalesProject.city.is_not(None))
    missing_snapshot = and_(SalesProject.province.is_(None), SalesProject.city.is_(None))
    return or_(
        and_(has_snapshot, location_condition(SalesProject.province, SalesProject.city, scope)),
        and_(missing_snapshot, exists(select(1).where(
            OrganizationSite.organization_id == SalesProject.organization_id,
            location_condition(OrganizationSite.province, OrganizationSite.city, scope),
        ))),
    )


def require_organization_access(db: Session, organization_id: UUID, scope: AccountDataScope) -> None:
    """确认单位至少一个地点落在账号范围内；范围外与不存在都不泄露详情。"""

    if scope.unrestricted:
        return
    visible_id = db.scalar(select(Organization.id).where(
        Organization.id == organization_id,
        organization_visibility_condition(scope),
    ))
    if visible_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号不能访问该单位")


def require_customer_group_access(db: Session, group_id: UUID, scope: AccountDataScope) -> None:
    """确认跨省客户集团至少一个节点命中账号范围。"""

    if scope.unrestricted:
        return
    visible_id = db.scalar(select(CustomerGroup.id).where(
        CustomerGroup.id == group_id,
        customer_group_visibility_condition(scope),
    ))
    if visible_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号不能访问该客户集团")


def require_competitor_access(
    db: Session,
    competitor_id: UUID,
    scope: AccountDataScope,
    creator_username: str | None = None,
) -> None:
    """确认同行至少一个据点或成交客户落在账号范围内。"""

    if scope.unrestricted:
        return
    visible_id = db.scalar(select(Competitor.id).where(
        Competitor.id == competitor_id,
        competitor_visibility_condition(scope, creator_username),
    ))
    if visible_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号不能访问该同行")


def require_unite_deal_access(db: Session, deal_id: UUID, scope: AccountDataScope) -> None:
    """确认优纳特订单自身或所属单位与账号范围有区域交集。"""

    if scope.unrestricted:
        return
    visible_id = db.scalar(select(SalesProject.id).where(
        SalesProject.id == deal_id,
        unite_deal_visibility_condition(scope),
    ))
    if visible_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号不能访问该成交订单")


def competitor_order_location_condition(scope: AccountDataScope):
    """在已关联成交单位的查询中，按订单快照或旧数据的单位所在地判断同行订单权限。"""

    if scope.unrestricted:
        return true()
    has_snapshot = and_(CompetitorDeal.province.is_not(None), CompetitorDeal.city.is_not(None))
    missing_snapshot = and_(CompetitorDeal.province.is_(None), CompetitorDeal.city.is_(None))
    return or_(
        and_(has_snapshot, location_condition(CompetitorDeal.province, CompetitorDeal.city, scope)),
        and_(missing_snapshot, location_condition(CompetitorCustomer.province, CompetitorCustomer.city, scope)),
    )


def competitor_order_visibility_condition(scope: AccountDataScope):
    """为未关联成交单位的查询生成同行订单权限条件，防止单位表隐式笛卡尔积。"""

    if scope.unrestricted:
        return true()
    has_snapshot = and_(CompetitorDeal.province.is_not(None), CompetitorDeal.city.is_not(None))
    missing_snapshot = and_(CompetitorDeal.province.is_(None), CompetitorDeal.city.is_(None))
    customer_match = exists(select(1).where(
        CompetitorCustomer.id == CompetitorDeal.competitor_customer_id,
        location_condition(CompetitorCustomer.province, CompetitorCustomer.city, scope),
    ))
    return or_(
        and_(has_snapshot, location_condition(CompetitorDeal.province, CompetitorDeal.city, scope)),
        and_(missing_snapshot, customer_match),
    )


def competitor_order_is_visible(
    scope: AccountDataScope,
    deal: CompetitorDeal,
    customer: CompetitorCustomer,
) -> bool:
    """在响应组装时复用订单所在地优先规则，避免已加载关系泄露范围外订单。"""

    if scope.unrestricted:
        return True
    province = getattr(deal, "province", None)
    city = getattr(deal, "city", None)
    has_snapshot = bool(province) and bool(city)
    missing_snapshot = not province and not city
    if has_snapshot:
        return location_is_visible(scope, province, city)
    if missing_snapshot:
        return location_is_visible(scope, customer.province, customer.city)
    return False


def competitor_deal_visibility_condition(scope: AccountDataScope):
    """仅以可见成交订单判断同行主档是否允许编辑，避免据点扩大写权限。"""

    if scope.unrestricted:
        return true()
    return exists(
        select(1)
        .select_from(CompetitorDeal)
        .join(CompetitorCustomer, CompetitorCustomer.id == CompetitorDeal.competitor_customer_id)
        .where(
            CompetitorCustomer.competitor_id == Competitor.id,
            competitor_order_location_condition(scope),
        )
    )


def competitor_visibility_condition(scope: AccountDataScope, creator_username: str | None = None):
    """同行命中区域即可见；新建但尚无据点的主档仅对创建者临时可见。"""

    if scope.unrestricted:
        return true()
    site_match = exists(select(1).where(
        CompetitorSite.competitor_id == Competitor.id,
        location_condition(CompetitorSite.province, CompetitorSite.city, scope),
    ))
    deal_match = competitor_deal_visibility_condition(scope)
    conditions = [site_match, deal_match]
    if creator_username:
        conditions.append(exists(select(1).where(
            AuditLog.actor_username == creator_username,
            AuditLog.action == "新增同行",
            AuditLog.detail["资源"].as_string() == "competitors",
            AuditLog.detail["记录ID"].as_string() == cast(Competitor.id, String),
        )))
    return or_(*conditions)
