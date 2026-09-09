"""管理员数据后台模式：校验非目标单位数据表的完整业务字段。"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import (
    ChannelPartnerType,
    CompetitorCustomerLevel,
    CompetitorMatchStatus,
    CompetitorRegionLevel,
    CompetitorSiteType,
    CompetitorStrengthLevel,
    CooperationLevel,
    IntelligenceConfidence,
    IntelligenceSourceType,
    OpportunityStage,
    SalesActivityType,
)
from app.schemas import CompetitorCustomerRead, CompetitorSiteRead
from app.sales_coverage import SalesCoverageLevel, normalize_coverage_scope


class AdminDataInput(BaseModel):
    """为后台全字段表单提供统一的空白清理和多余字段拒绝策略。"""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class AdminDataMutation(BaseModel):
    """统一承载资源专属字段，具体类型由受控资源注册表继续校验。"""

    data: dict[str, Any]


class AdminDataPage(BaseModel):
    """统一返回后台分页记录，字段集合由当前资源定义决定。"""

    items: list[dict[str, Any]]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class AdminDataOption(BaseModel):
    """为外键搜索控件返回稳定 ID 与可读名称。"""

    value: UUID
    label: str


class SalesOfficeAdminInput(AdminDataInput):
    """销售常驻点全部可维护业务字段。"""

    name: str = Field(min_length=2, max_length=160)
    city: str = Field(min_length=2, max_length=60)
    address: str | None = Field(default=None, max_length=500)
    longitude: float = Field(ge=72.004, le=137.8347)
    latitude: float = Field(ge=0.8293, le=55.8271)
    coverage_radius_km: int = Field(ge=1, le=2000)
    is_active: bool = True


class ChannelPartnerAdminInput(AdminDataInput):
    """经销商、代理商和合作伙伴全部可维护业务字段。"""

    name: str = Field(min_length=2, max_length=160)
    partner_type: ChannelPartnerType
    address: str = Field(min_length=2, max_length=500)
    longitude: float | None = Field(default=None, ge=72.004, le=137.8347)
    latitude: float | None = Field(default=None, ge=0.8293, le=55.8271)
    display_longitude: float = Field(ge=72.004, le=137.8347)
    display_latitude: float = Field(ge=0.8293, le=55.8271)
    authorized_coverage_area: str | None = Field(default=None, max_length=500)
    coverage_radius_km: int = Field(ge=1, le=2000)
    authorized_product_lines: list[Annotated[str, Field(min_length=1, max_length=160)]] | None = Field(default=None, max_length=50)
    cooperation_level: CooperationLevel
    contract_info: str | None = Field(default=None, max_length=5000)
    notes: str | None = Field(default=None, max_length=5000)
    is_active: bool = True

    @model_validator(mode="after")
    def require_coordinate_pair(self) -> "ChannelPartnerAdminInput":
        """真实业务坐标必须成对填写，避免地图读取半套位置。"""

        if (self.longitude is None) != (self.latitude is None):
            raise ValueError("经度和纬度必须同时填写或同时留空")
        return self


class CustomerGroupAdminInput(AdminDataInput):
    """客户集团主档全部可维护业务字段。"""

    name: str = Field(min_length=2, max_length=255)
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class CustomerGroupUnitAdminInput(AdminDataInput):
    """客户集团总部或分支节点全部可维护业务字段。"""

    group_id: UUID
    parent_id: UUID | None = None
    name: str = Field(min_length=2, max_length=255)
    is_headquarters: bool = False
    address: str = Field(min_length=2, max_length=500)
    province: str = Field(min_length=2, max_length=60)
    city: str = Field(min_length=2, max_length=60)
    longitude: float = Field(ge=72.004, le=137.8347)
    latitude: float = Field(ge=0.8293, le=55.8271)
    is_won: bool = False
    actual_sales_amount: Decimal = Field(default=Decimal(0), ge=0)
    opportunity_stage: OpportunityStage | None = None
    estimated_opportunity_amount: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_tree_and_amount(self) -> "CustomerGroupUnitAdminInput":
        """保持总部根节点、分支父节点和实际成交金额口径一致。"""

        if self.is_headquarters != (self.parent_id is None):
            raise ValueError("总部不能选择父节点，分支必须选择父节点")
        if self.is_won != (self.actual_sales_amount > 0):
            raise ValueError("已成交节点必须填写大于 0 的实际销售额，未成交节点金额必须为 0")
        return self


class CustomerGroupUnitProfileInput(AdminDataInput):
    """在客户集团完整档案内描述一个总部或分支，并用草稿键表达同批次父子关系。"""

    id: UUID | None = None
    draft_key: str = Field(min_length=1, max_length=80)
    parent_draft_key: str | None = Field(default=None, min_length=1, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    is_headquarters: bool = False
    address: str = Field(min_length=2, max_length=500)
    province: str = Field(min_length=2, max_length=60)
    city: str = Field(min_length=2, max_length=60)
    longitude: float = Field(ge=72.004, le=137.8347)
    latitude: float = Field(ge=0.8293, le=55.8271)
    is_won: bool = False
    actual_sales_amount: Decimal = Field(default=Decimal(0), ge=0)
    opportunity_stage: OpportunityStage | None = None
    estimated_opportunity_amount: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_role_and_amount(self) -> "CustomerGroupUnitProfileInput":
        """保持根节点角色与成交金额口径一致，树的跨记录校验交给完整档案。"""

        if self.is_headquarters != (self.parent_draft_key is None):
            raise ValueError("总部不能选择父节点，分支必须选择父节点")
        if self.is_won != (self.actual_sales_amount > 0):
            raise ValueError("已成交节点必须填写大于 0 的实际销售额，未成交节点金额必须为 0")
        return self


class CustomerGroupProfileInput(CustomerGroupAdminInput):
    """一次校验集团主档及完整单位树，供单事务同步使用。"""

    units: list[CustomerGroupUnitProfileInput] = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def validate_unit_tree(self) -> "CustomerGroupProfileInput":
        """拒绝重复键、重复单位名、多个总部、循环和未连接分支。"""

        keys = [item.draft_key for item in self.units]
        ids = [item.id for item in self.units if item.id is not None]
        names = [item.name.casefold() for item in self.units]
        if len(set(keys)) != len(keys):
            raise ValueError("集团单位草稿标识不能重复")
        if len(set(ids)) != len(ids):
            raise ValueError("集团单位 ID 不能重复")
        if len(set(names)) != len(names):
            raise ValueError("同一集团内的单位名称不能重复")
        headquarters = [item for item in self.units if item.is_headquarters]
        if len(headquarters) != 1:
            raise ValueError("每个客户集团必须且只能有一个总部")

        parent_by_key = {item.draft_key: item.parent_draft_key for item in self.units}
        root_key = headquarters[0].draft_key
        for item in self.units:
            if item.parent_draft_key is not None and item.parent_draft_key not in parent_by_key:
                raise ValueError(f"单位“{item.name}”选择的父级不存在")
            visited: set[str] = set()
            current_key = item.draft_key
            while current_key != root_key:
                if current_key in visited:
                    raise ValueError("集团单位层级不能形成循环")
                visited.add(current_key)
                parent_key = parent_by_key.get(current_key)
                if parent_key is None:
                    raise ValueError(f"单位“{item.name}”未连接到集团总部")
                current_key = parent_key
        return self


class CustomerGroupUnitProfileRead(BaseModel):
    """返回集团档案内一条可继续编辑的单位及其父级草稿键。"""

    id: UUID
    draft_key: str
    parent_draft_key: str | None
    name: str
    is_headquarters: bool
    address: str
    province: str
    city: str
    longitude: float
    latitude: float
    is_won: bool
    actual_sales_amount: Decimal
    opportunity_stage: OpportunityStage | None
    estimated_opportunity_amount: Decimal | None
    created_at: datetime
    updated_at: datetime


class CustomerGroupProfileRead(CustomerGroupAdminInput):
    """客户集团管理页按需读取的完整主档和单位树。"""

    id: UUID
    units: list[CustomerGroupUnitProfileRead]
    created_at: datetime
    updated_at: datetime


class CustomerGroupAdminListItem(BaseModel):
    """客户集团主列表的一行聚合数据，避免前端逐集团加载单位树。"""

    id: UUID
    name: str
    color: str
    headquarters_name: str | None
    headquarters_city: str | None
    branch_count: int = Field(ge=0)
    won_unit_count: int = Field(ge=0)
    active_opportunity_count: int = Field(ge=0)
    actual_sales_amount: Decimal = Field(ge=0)
    estimated_opportunity_amount: Decimal = Field(ge=0)


class CustomerGroupAdminListPage(BaseModel):
    """客户集团聚合列表的稳定分页响应。"""

    items: list[CustomerGroupAdminListItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class CompetitorAdminInput(AdminDataInput):
    """同行主档全部可维护业务字段。"""

    name: str = Field(min_length=2, max_length=255)
    website_url: str | None = Field(default=None, max_length=1000, pattern=r"^https?://")
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    description: str | None = Field(default=None, max_length=5000)
    is_active: bool = True


class CompetitorAdminListItem(CompetitorAdminInput):
    """同行主列表的一行聚合数据，只返回管理页仍展示的业务摘要。"""

    id: UUID
    primary_site_name: str | None
    primary_site_city: str | None
    site_count: int = Field(ge=0)
    customer_count: int = Field(ge=0)
    linked_customer_count: int = Field(ge=0)
    pending_link_count: int = Field(ge=0)
    deal_count: int = Field(ge=0)
    total_amount: Decimal = Field(ge=0)
    created_at: datetime
    updated_at: datetime


class CompetitorAdminListPage(BaseModel):
    """同行聚合列表的稳定分页响应。"""

    items: list[CompetitorAdminListItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class CompetitorAdminSummary(BaseModel):
    """汇总当前账号覆盖范围内可见的同行据点、单位和订单。"""

    site_count: int = Field(ge=0)
    customer_count: int = Field(ge=0)
    linked_customer_count: int = Field(ge=0)
    deal_count: int = Field(ge=0)
    total_amount: Decimal = Field(ge=0)


class CompetitorAdminDetail(CompetitorAdminInput):
    """成交订单抽屉使用的同行主档及区域裁剪后的业务详情。"""

    id: UUID
    summary: CompetitorAdminSummary
    sites: list[CompetitorSiteRead]
    customers: list[CompetitorCustomerRead]
    scope_limited: bool
    created_at: datetime
    updated_at: datetime


class CompetitorSiteAdminInput(AdminDataInput):
    """同行据点全部可维护业务字段。"""

    competitor_id: UUID
    name: str = Field(min_length=2, max_length=255)
    site_type: CompetitorSiteType
    address: str = Field(min_length=2, max_length=500)
    province: str = Field(min_length=2, max_length=60)
    city: str = Field(min_length=2, max_length=60)
    longitude: float = Field(ge=72.004, le=137.8347)
    latitude: float = Field(ge=0.8293, le=55.8271)
    source_type: IntelligenceSourceType
    source_reference: str = Field(min_length=2, max_length=500)
    source_url: str | None = Field(default=None, max_length=1000)
    confidence: IntelligenceConfidence
    notes: str | None = Field(default=None, max_length=5000)
    is_primary: bool = False


class CompetitorCustomerAdminInput(AdminDataInput):
    """同行成交单位全部可维护业务字段，待补地址记录允许暂缺地址和坐标。"""

    competitor_id: UUID
    name: str = Field(min_length=2, max_length=255)
    customer_level: CompetitorCustomerLevel
    address: str | None = Field(default=None, max_length=500)
    province: str = Field(min_length=2, max_length=60)
    city: str = Field(min_length=2, max_length=60)
    longitude: float | None = Field(default=None, ge=72.004, le=137.8347)
    latitude: float | None = Field(default=None, ge=0.8293, le=55.8271)
    source_type: IntelligenceSourceType
    source_reference: str = Field(min_length=2, max_length=500)
    source_url: str | None = Field(default=None, max_length=1000)
    confidence: IntelligenceConfidence
    first_observed_at: date | None = None
    last_verified_at: date | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def validate_coordinate_pair(self) -> "CompetitorCustomerAdminInput":
        """经纬度必须同时填写或同时留空，避免产生半个地图点。"""

        if (self.longitude is None) != (self.latitude is None):
            raise ValueError("经度和纬度必须同时填写或同时留空")
        return self


class CompetitorDealProductAdminInput(AdminDataInput):
    """定义同行成交订单中的一条可编辑产品品牌明细。"""

    id: UUID | None = None
    product_name: str = Field(min_length=1, max_length=255)
    brand: str | None = Field(default=None, max_length=255)
    specification_model: str | None = Field(default=None, max_length=255)
    product_image_url: str | None = Field(default=None, max_length=1000)
    unit_price: Decimal | None = Field(default=None, gt=0)
    quantity: Decimal | None = Field(default=None, gt=0)
    line_total: Decimal = Field(ge=0)


class CompetitorDealAdminInput(AdminDataInput):
    """同行逐笔成交记录全部可维护业务字段。"""

    competitor_customer_id: UUID
    project_name: str = Field(min_length=2, max_length=255)
    deal_type: str | None = Field(default=None, min_length=1, max_length=80)
    # 兼容迁移期间的旧表单；服务层会把这些字段转换为第一条 products 明细。
    product_name: str | None = Field(default=None, max_length=255)
    specification_model: str | None = Field(default=None, max_length=255)
    product_image_url: str | None = Field(default=None, max_length=1000)
    unit_price: Decimal | None = Field(default=None, gt=0)
    quantity: Decimal | None = Field(default=None, gt=0)
    supplier_name: str | None = Field(default=None, max_length=255)
    amount: Decimal = Field(gt=0)
    signed_at: date | None = None
    source_type: IntelligenceSourceType | None = None
    source_reference: str | None = Field(default=None, min_length=2, max_length=500)
    source_url: str | None = Field(default=None, max_length=1000)
    confidence: IntelligenceConfidence | None = None
    notes: str | None = Field(default=None, max_length=5000)
    products: list[CompetitorDealProductAdminInput] = Field(default_factory=list, max_length=100)


class CompetitorStrengthRegionAdminInput(AdminDataInput):
    """同行人工强势区域全部可维护业务字段。"""

    competitor_id: UUID
    region_level: CompetitorRegionLevel
    province: str = Field(min_length=2, max_length=60)
    city: str | None = Field(default=None, max_length=60)
    strength_level: CompetitorStrengthLevel
    source_type: IntelligenceSourceType
    source_reference: str = Field(min_length=2, max_length=500)
    source_url: str | None = Field(default=None, max_length=1000)
    confidence: IntelligenceConfidence
    basis: str = Field(min_length=2, max_length=5000)

    @model_validator(mode="after")
    def validate_region_scope(self) -> "CompetitorStrengthRegionAdminInput":
        """省级区域不填写城市，市级区域必须明确城市。"""

        if (self.region_level is CompetitorRegionLevel.province) != (self.city is None):
            raise ValueError("省级区域不能填写城市，市级区域必须填写城市")
        return self


class CompetitorLinkAdminInput(AdminDataInput):
    """同行成交单位与正式目标单位匹配记录的全部可维护字段。"""

    competitor_customer_id: UUID
    organization_id: UUID
    match_status: CompetitorMatchStatus
    match_method: str = Field(min_length=1, max_length=120)
    match_confidence: IntelligenceConfidence
    matched_by: str | None = Field(default=None, max_length=120)
    matched_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=5000)


class SalespersonAdminInput(AdminDataInput):
    """销售人员主档和地图 Pin 的全部可维护业务字段。"""

    employee_code: str = Field(min_length=1, max_length=40)
    display_name: str = Field(min_length=2, max_length=120)
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    coverage_center_longitude: float = Field(ge=72.004, le=137.8347)
    coverage_center_latitude: float = Field(ge=0.8293, le=55.8271)
    is_active: bool = True


class SalespersonCoverageScopeFields(AdminDataInput):
    """统一校验市、省、大区和全国覆盖所需的条件字段。"""

    scope_level: SalesCoverageLevel
    scope_name: str = Field(min_length=1, max_length=60)
    province: str | None = Field(default=None, max_length=60)
    city: str | None = Field(default=None, max_length=60)
    amap_adcode: str | None = Field(default=None, max_length=12)

    @model_validator(mode="after")
    def normalize_scope(self) -> "SalespersonCoverageScopeFields":
        """把省份全称归一为短名称，并拒绝与层级不相符的多余字段。"""

        normalized = normalize_coverage_scope(
            self.scope_level,
            self.scope_name,
            self.province,
            self.city,
            self.amap_adcode,
        )
        self.scope_name = normalized.scope_name
        self.province = normalized.province
        self.city = normalized.city
        self.amap_adcode = normalized.amap_adcode
        return self


class SalespersonCoverageScopeAdminInput(SalespersonCoverageScopeFields):
    """通用后台兼容入口使用的销售覆盖范围完整字段。"""

    salesperson_id: UUID


class SalesActivityAdminInput(AdminDataInput):
    """销售活动流水全部可维护业务字段。"""

    salesperson_id: UUID
    organization_id: UUID | None = None
    activity_type: SalesActivityType
    occurred_at: datetime
    province: str = Field(min_length=2, max_length=60)
    city: str = Field(min_length=2, max_length=60)
    amap_adcode: str = Field(pattern=r"^[0-9]{6}$")
    notes: str | None = Field(default=None, max_length=5000)


class SalespersonCoverageScopeProfileInput(SalespersonCoverageScopeFields):
    """在销售人员完整档案内新增或同步一条覆盖范围。"""

    id: UUID | None = None


class SalesActivityProfileInput(AdminDataInput):
    """在销售人员完整档案内新增或同步一条销售活动。"""

    id: UUID | None = None
    organization_id: UUID | None = None
    activity_type: SalesActivityType
    occurred_at: datetime
    province: str = Field(min_length=2, max_length=60)
    city: str = Field(min_length=2, max_length=60)
    amap_adcode: str = Field(pattern=r"^[0-9]{6}$")
    notes: str | None = Field(default=None, max_length=5000)


class SalespersonProfileInput(SalespersonAdminInput):
    """一次校验销售人员主档、覆盖范围和销售活动，供原子保存使用。"""

    coverage_scopes: list[SalespersonCoverageScopeProfileInput] = Field(default_factory=list, max_length=1000)
    activities: list[SalesActivityProfileInput] = Field(default_factory=list, max_length=5000)

    @model_validator(mode="after")
    def validate_coverage_collection(self) -> "SalespersonProfileInput":
        """禁止重复范围，并确保全国范围不会与其他覆盖记录并存。"""

        scope_keys = [(item.scope_level, item.scope_name) for item in self.coverage_scopes]
        if len(scope_keys) != len(set(scope_keys)):
            raise ValueError("同一销售人员不能重复添加相同覆盖范围")
        if any(level is SalesCoverageLevel.national for level, _name in scope_keys) and len(scope_keys) > 1:
            raise ValueError("全国覆盖不能与其他覆盖范围同时添加")
        return self


class SalespersonCoverageScopeProfileRead(BaseModel):
    """返回销售人员档案内一条可继续编辑的分级覆盖范围。"""

    id: UUID
    scope_level: SalesCoverageLevel
    scope_name: str
    province: str | None
    city: str | None
    amap_adcode: str | None


class SalesActivityProfileRead(BaseModel):
    """返回销售人员档案内一条活动及其可读单位名称。"""

    id: UUID
    organization_id: UUID | None
    organization_name: str | None
    activity_type: SalesActivityType
    occurred_at: datetime
    province: str
    city: str
    amap_adcode: str
    notes: str | None


class SalespersonProfileRead(SalespersonAdminInput):
    """销售人员管理页所需的完整聚合档案。"""

    id: UUID
    coverage_scopes: list[SalespersonCoverageScopeProfileRead]
    activities: list[SalesActivityProfileRead]
    created_at: datetime
    updated_at: datetime


class SalespersonAdminListItem(BaseModel):
    """销售主列表的一行聚合数据，避免前端逐人补查统计。"""

    id: UUID
    employee_code: str
    display_name: str
    color: str
    coverage_scopes: list[str]
    coverage_scope_total: int = Field(ge=0)
    actual_sales_amount: Decimal = Field(ge=0)
    visit_count: int = Field(ge=0)
    demonstration_count: int = Field(ge=0)
    marketing_event_count: int = Field(ge=0)
    is_active: bool


class SalespersonAdminListPage(BaseModel):
    """销售人员聚合列表的稳定分页响应。"""

    items: list[SalespersonAdminListItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
