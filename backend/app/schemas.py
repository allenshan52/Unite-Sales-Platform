"""API 数据模式：通过 Pydantic 分隔公开目录字段与管理员单位详情。"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.models import (
    ChannelPartnerType,
    CompetitorCustomerLevel,
    CompetitorMatchStatus,
    CompetitorRegionLevel,
    CompetitorSiteType,
    CompetitorStrengthLevel,
    CooperationLevel,
    CustomerStatus,
    EvidenceKind,
    GeocodeStatus,
    IntelligenceConfidence,
    IntelligenceSourceType,
    OpportunityStage,
    OrganizationType,
    ReviewStatus,
    UserRole,
)
from app.sales_coverage import SalesCoverageLevel, normalize_coverage_scope


class PublicOrganizationCompetitorLinkRead(BaseModel):
    """单位数据库中的同行签约摘要，仅返回已确认关系和可公开情报字段。"""

    competitor_id: UUID
    competitor_name: str
    competitor_color: str
    competitor_customer_id: UUID
    customer_level: CompetitorCustomerLevel
    deal_count: int = Field(ge=0)
    total_amount: Decimal
    source_type: IntelligenceSourceType
    confidence: IntelligenceConfidence
    match_confidence: IntelligenceConfidence


class EvidenceInput(BaseModel):
    """新增单位时一条可追溯的官方证据。"""

    evidence_kind: EvidenceKind
    title: str = Field(min_length=2, max_length=255)
    source_url: HttpUrl
    published_at: date | None = None
    excerpt: str | None = Field(default=None, max_length=2000)


class SiteInput(BaseModel):
    """新增或编辑时的单位地点；坐标须与已定位状态一致。"""

    site_name: str | None = Field(default=None, max_length=160)
    raw_address: str | None = Field(default=None, max_length=500)
    address: str | None = Field(default=None, max_length=500)
    province: str | None = Field(default=None, max_length=60)
    city: str | None = Field(default=None, max_length=60)
    district: str | None = Field(default=None, max_length=80)
    amap_adcode: str | None = Field(default=None, max_length=12)
    geocode_status: GeocodeStatus = GeocodeStatus.pending
    geocode_confidence: int | None = Field(default=None, ge=0, le=100)
    longitude: float | None = Field(default=None, ge=73, le=136)
    latitude: float | None = Field(default=None, ge=3, le=54)
    is_primary: bool = True


class AmapLocationSearchRead(BaseModel):
    """公司地点搜索候选；坐标保持高德 GCJ-02，供后台表单直接回填。"""

    name: str
    address: str
    province: str
    city: str
    district: str
    amap_adcode: str
    longitude: str
    latitude: str


class OrganizationCreate(BaseModel):
    """正式入库输入；高校和研究院在服务端强制要求至少一项纳入证据。"""

    name: str = Field(min_length=2, max_length=255)
    organization_type: OrganizationType
    industry: str | None = Field(default=None, max_length=120)
    inclusion_reason: str | None = Field(default=None, max_length=2000)
    is_sports_exception: bool = False
    parent_group: str | None = Field(default=None, max_length=255)
    website: HttpUrl | None = None
    unified_social_credit_code: str | None = Field(default=None, min_length=18, max_length=18)
    notes: str | None = Field(default=None, max_length=5000)
    sites: list[SiteInput] = Field(default_factory=list)
    evidences: list[EvidenceInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_academic_evidence(self) -> "OrganizationCreate":
        """阻止无官方专业/研究依据的高校、研究院绕过业务筛选规则。"""

        if self.organization_type in {OrganizationType.university, OrganizationType.research_institute} and not self.evidences:
            raise ValueError("高校和研究院必须附至少一条专业、研究方向或官方名录证据")
        if self.is_sports_exception and self.organization_type is not OrganizationType.university:
            raise ValueError("体育例外仅适用于高校类型")
        return self


class SiteUpdate(BaseModel):
    """管理员可修正的主地点字段；服务层基于现值校验状态与坐标组合。"""

    site_name: str | None = Field(default=None, max_length=160)
    raw_address: str | None = Field(default=None, max_length=500)
    address: str | None = Field(default=None, max_length=500)
    province: str | None = Field(default=None, max_length=60)
    city: str | None = Field(default=None, max_length=60)
    district: str | None = Field(default=None, max_length=80)
    amap_adcode: str | None = Field(default=None, max_length=12)
    geocode_status: GeocodeStatus | None = None
    geocode_confidence: int | None = Field(default=None, ge=0, le=100)
    longitude: float | None = Field(default=None, ge=73, le=136)
    latitude: float | None = Field(default=None, ge=3, le=54)


class ContactUpdate(BaseModel):
    """管理员在单位编辑页新增或修改的一条受保护联系人记录。"""

    id: UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    department: str | None = Field(default=None, max_length=160)
    title: str | None = Field(default=None, max_length=160)
    mobile: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=254)
    is_primary: bool = False
    is_active: bool = True
    notes: str | None = Field(default=None, max_length=5000)


class OpportunityUpdate(BaseModel):
    """管理员在单位编辑页维护的一条商机及其推进动作。"""

    id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    stage: OpportunityStage = OpportunityStage.identified
    estimated_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    ai_summary: str | None = Field(default=None, max_length=5000)
    next_action: str | None = Field(default=None, max_length=2000)
    next_action_at: date | None = None


class SalesProjectProductUpdate(BaseModel):
    """定义优纳特成交项目中可新增、排序和编辑的一条产品品牌明细。"""

    id: UUID | None = None
    product_name: str = Field(min_length=1, max_length=255)
    brand: str | None = Field(default=None, max_length=255)
    specification_model: str | None = Field(default=None, max_length=255)
    unit_price: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=3)
    line_total: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


class SalesProjectUpdate(BaseModel):
    """管理员在单位编辑页维护的一条成交项目及其产品、供应和地域明细。"""

    id: UUID | None = None
    opportunity_id: UUID | None = None
    salesperson_id: UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    contract_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    # 兼容迁移期间仍在运行的旧前端；新界面只提交 products。
    unit_price: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=3)
    supplier_name: str | None = Field(default=None, max_length=255)
    specification_model: str | None = Field(default=None, max_length=255)
    location_name: str | None = Field(default=None, max_length=255)
    province: str | None = Field(default=None, max_length=60)
    city: str | None = Field(default=None, max_length=60)
    signed_at: date | None = None
    project_detail: str | None = Field(default=None, max_length=5000)
    products: list[SalesProjectProductUpdate] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_location_pair(self) -> "SalesProjectUpdate":
        """要求订单省市成对出现，使单位编辑入口与成交订单入口保持相同数据约束。"""

        if bool(self.province) != bool(self.city):
            raise ValueError("成交单位所在地的省份和城市必须同时填写")
        if self.location_name and not self.province:
            raise ValueError("填写所在地名称时必须同时填写省份和城市")
        return self


class OrganizationUpdate(BaseModel):
    """管理员原子编辑单位主档、主地点及联系人、成交项目和商机集合；证据与审计保持独立。"""

    version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    organization_type: OrganizationType | None = None
    industry: str | None = Field(default=None, max_length=120)
    customer_status: CustomerStatus | None = None
    review_status: ReviewStatus | None = None
    inclusion_reason: str | None = Field(default=None, max_length=2000)
    is_sports_exception: bool | None = None
    parent_group: str | None = Field(default=None, max_length=255)
    website: HttpUrl | None = None
    unified_social_credit_code: str | None = Field(default=None, min_length=18, max_length=18)
    recent_follow_up_at: datetime | None = None
    recent_follow_up_content: str | None = Field(default=None, max_length=5000)
    follow_up_owner: str | None = Field(default=None, max_length=120)
    cooperation_intent: str | None = Field(default=None, max_length=500)
    cooperation_level: CooperationLevel | None = None
    notes: str | None = Field(default=None, max_length=5000)
    primary_site: SiteUpdate | None = None
    contacts: list[ContactUpdate] | None = Field(default=None, max_length=100)
    sales_projects: list[SalesProjectUpdate] | None = Field(default=None, max_length=100)
    opportunities: list[OpportunityUpdate] | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_explicit_sports_exception(self) -> "OrganizationUpdate":
        """在请求同时给出类型与体育例外时尽早阻止明显冲突。"""

        if self.is_sports_exception and self.organization_type is not None and self.organization_type is not OrganizationType.university:
            raise ValueError("体育例外仅适用于高校类型")
        return self


class OrganizationAdminCreate(BaseModel):
    """管理员一次新增单位主档和关联记录；必填规则集中在此，便于后续调整。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=255)
    organization_type: OrganizationType
    industry: str | None = Field(default=None, max_length=120)
    customer_status: CustomerStatus = CustomerStatus.potential
    review_status: ReviewStatus = ReviewStatus.pending
    inclusion_reason: str | None = Field(default=None, max_length=2000)
    is_sports_exception: bool = False
    parent_group: str | None = Field(default=None, max_length=255)
    website: HttpUrl | None = None
    unified_social_credit_code: str | None = Field(default=None, min_length=18, max_length=18)
    recent_follow_up_at: datetime | None = None
    recent_follow_up_content: str | None = Field(default=None, max_length=5000)
    follow_up_owner: str | None = Field(default=None, max_length=120)
    cooperation_intent: str | None = Field(default=None, max_length=500)
    cooperation_level: CooperationLevel | None = None
    notes: str | None = Field(default=None, max_length=5000)
    primary_site: SiteUpdate
    contacts: list[ContactUpdate] = Field(default_factory=list, max_length=100)
    sales_projects: list[SalesProjectUpdate] = Field(default_factory=list, max_length=100)
    opportunities: list[OpportunityUpdate] = Field(default_factory=list, max_length=100)
    evidences: list[EvidenceInput] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_admin_create(self) -> "OrganizationAdminCreate":
        """要求基本行政区并拒绝复用其他单位的子记录 ID，防止跨单位关联。"""

        if not self.primary_site.province or not self.primary_site.city:
            raise ValueError("新增单位必须填写省份和城市")
        if self.is_sports_exception and self.organization_type is not OrganizationType.university:
            raise ValueError("体育例外仅适用于高校类型")
        child_ids = [
            *(item.id for item in self.contacts),
            *(item.id for item in self.sales_projects),
            *(product.id for item in self.sales_projects for product in item.products),
            *(item.id for item in self.opportunities),
            *(item.opportunity_id for item in self.sales_projects),
        ]
        if any(item_id is not None for item_id in child_ids):
            raise ValueError("新增单位的关联记录不能携带已有 ID")
        return self


class SiteRead(BaseModel):
    """审核列表和详情抽屉使用的地点输出。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    site_name: str | None
    raw_address: str | None
    address: str | None
    province: str | None
    city: str | None
    district: str | None
    amap_adcode: str | None
    geocode_status: GeocodeStatus
    geocode_confidence: int | None
    longitude: float | None
    latitude: float | None
    is_primary: bool


class EvidenceRead(BaseModel):
    """对管理端公开的来源追溯信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    evidence_kind: EvidenceKind
    title: str
    source_url: str
    retrieved_at: date
    excerpt: str | None


class ContactRead(ContactUpdate):
    """管理员单位详情返回的联系人记录。"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID


class OpportunityRead(OpportunityUpdate):
    """管理员单位详情返回的商机记录。"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID


class SalesProjectProductRead(SalesProjectProductUpdate):
    """返回已持久化的优纳特成交产品明细。"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID


class SalesProjectRead(SalesProjectUpdate):
    """管理员单位详情返回的成交项目记录。"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    products: list[SalesProjectProductRead] = Field(default_factory=list)


class OrganizationRead(BaseModel):
    """单位详情和列表的统一响应，防止前端自行拼接状态或地址。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    organization_type: OrganizationType
    industry: str | None
    customer_status: CustomerStatus
    review_status: ReviewStatus
    inclusion_reason: str | None
    is_sports_exception: bool
    parent_group: str | None
    website: str | None
    unified_social_credit_code: str | None
    recent_follow_up_at: datetime | None
    recent_follow_up_content: str | None
    follow_up_owner: str | None
    cooperation_intent: str | None
    cooperation_level: CooperationLevel | None
    notes: str | None
    archived_at: datetime | None
    version: int
    sites: list[SiteRead]
    evidences: list[EvidenceRead]
    contacts: list[ContactRead]
    sales_projects: list[SalesProjectRead]
    opportunities: list[OpportunityRead]
    created_at: datetime
    updated_at: datetime


class OrganizationPage(BaseModel):
    """服务端分页结果，确保两万条数据不会一次性传到浏览器。"""

    items: list[OrganizationRead]
    total: int
    page: int
    page_size: int


class PublicSiteRead(BaseModel):
    """公开主站所需的行政区地点，不包含地址、坐标或编码状态。"""

    model_config = ConfigDict(from_attributes=True)

    province: str | None
    city: str | None
    district: str | None
    is_primary: bool


class PublicOrganizationRead(BaseModel):
    """主站列表实际展示的单位字段，不暴露备注和证据详情。"""

    id: UUID
    name: str
    organization_type: OrganizationType
    industry: str | None
    customer_status: CustomerStatus
    review_status: ReviewStatus
    inclusion_reason: str | None
    is_sports_exception: bool
    parent_group: str | None
    website: str | None
    recent_follow_up_at: datetime | None
    recent_follow_up_content: str | None
    cooperation_intent: str | None
    cooperation_level: CooperationLevel | None
    evidence_count: int
    sites: list[PublicSiteRead]
    competitor_contracts: list[PublicOrganizationCompetitorLinkRead] = Field(default_factory=list)


class PublicOrganizationPage(BaseModel):
    """公开单位目录的分页响应，只承载主站允许显示的数据。"""

    items: list[PublicOrganizationRead]
    total: int
    page: int
    page_size: int


class MapPoint(BaseModel):
    """地图聚合前的轻量 pin 数据，只返回可信且已定位的主地点。"""

    id: UUID
    name: str
    organization_type: OrganizationType
    customer_status: CustomerStatus
    review_status: ReviewStatus
    longitude: float
    latitude: float
    province: str | None
    city: str | None
    district: str | None

    address: str | None
    active_opportunity_count: int = Field(ge=0)
    opportunity_stage: OpportunityStage | None
    estimated_opportunity_amount: Decimal = Field(ge=0)


class PublicWonCustomerDealRead(BaseModel):
    """优纳特已成交客户弹层中的逐笔实际成交项目。"""

    id: UUID
    name: str
    contract_amount: Decimal
    signed_at: date | None
    project_detail: str | None


class PublicWonCustomerMapPointRead(BaseModel):
    """同行地图叠加的已成交单位，只返回点位和实际成交字段。"""

    id: UUID
    name: str
    organization_type: OrganizationType
    industry: str | None
    customer_status: CustomerStatus
    review_status: ReviewStatus
    address: str | None
    province: str | None
    city: str | None
    district: str | None
    longitude: float
    latitude: float
    deal_count: int = Field(ge=0)
    actual_sales_amount: Decimal = Field(ge=0)
    deals: list[PublicWonCustomerDealRead]


class CustomerGroupUnitRead(BaseModel):
    """公开关系网中的单位节点；只包含地图、层级与销售状态字段。"""

    id: UUID
    parent_id: UUID | None
    name: str
    level: int = Field(ge=0)
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


class CustomerGroupHeadquartersRead(BaseModel):
    """首页首次加载的集团主档和总部节点，不提前传输分支。"""

    id: UUID
    name: str
    color: str
    headquarters: CustomerGroupUnitRead


class CustomerGroupSummaryRead(BaseModel):
    """从集团单位记录动态计算的公开汇总口径。"""

    branch_count: int = Field(ge=0)
    won_branch_count: int = Field(ge=0)
    active_opportunity_count: int = Field(ge=0)
    actual_sales_amount: Decimal
    provinces: list[str]
    cities: list[str]


class CustomerGroupDetailRead(BaseModel):
    """用户展开一个集团后返回的完整关系树和动态汇总。"""

    id: UUID
    name: str
    color: str
    headquarters_id: UUID
    summary: CustomerGroupSummaryRead
    units: list[CustomerGroupUnitRead]


class CompetitorSiteRead(BaseModel):
    """同行据点公开字段；地图用同一同行颜色区分总部、分部和服务点。"""

    id: UUID
    name: str
    site_type: CompetitorSiteType
    address: str
    province: str
    city: str
    longitude: float
    latitude: float
    source_type: IntelligenceSourceType
    source_reference: str
    source_url: str | None
    confidence: IntelligenceConfidence
    notes: str | None
    is_primary: bool


class CompetitorDealProductRead(BaseModel):
    """返回同行成交订单中的一条产品品牌明细。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_name: str
    brand: str | None
    specification_model: str | None
    product_image_url: str | None
    unit_price: Decimal | None
    quantity: Decimal | None
    line_total: Decimal


class CompetitorDealRead(BaseModel):
    """同行成交记录公开产品与可选来源字段，缺失情报保持为空。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_name: str
    deal_type: str | None
    # 兼容字段取第一条产品；新消费者应读取 products。
    product_name: str | None = None
    specification_model: str | None = None
    product_image_url: str | None = None
    unit_price: Decimal | None = None
    quantity: Decimal | None = None
    supplier_name: str | None = None
    amount: Decimal
    signed_at: date | None
    source_type: IntelligenceSourceType | None
    source_reference: str | None
    source_url: str | None
    confidence: IntelligenceConfidence | None
    notes: str | None
    products: list[CompetitorDealProductRead] = Field(default_factory=list)


class CompetitorCustomerRead(BaseModel):
    """同行成交单位节点；待补地址记录不返回地图坐标，但仍保留订单和关联。"""

    id: UUID
    name: str
    customer_level: CompetitorCustomerLevel
    address: str | None
    province: str
    city: str
    longitude: float | None
    latitude: float | None
    source_type: IntelligenceSourceType
    source_reference: str
    source_url: str | None
    confidence: IntelligenceConfidence
    first_observed_at: date | None
    last_verified_at: date | None
    notes: str | None
    linked_organization_id: UUID | None
    linked_organization_name: str | None
    match_status: CompetitorMatchStatus | None
    match_confidence: IntelligenceConfidence | None
    deals: list[CompetitorDealRead]


class CompetitorStrengthRegionRead(BaseModel):
    """由据点与成交活动实时推导的竞争区域，仅返回强度与评分依据。"""

    id: UUID
    region_level: CompetitorRegionLevel
    province: str
    city: str | None
    strength_level: CompetitorStrengthLevel
    source_type: IntelligenceSourceType
    source_reference: str
    source_url: str | None
    confidence: IntelligenceConfidence
    basis: str
    score: Decimal = Field(ge=0, le=1)
    site_count: int = Field(ge=0)
    customer_count: int = Field(ge=0)
    total_amount: Decimal = Field(ge=0)


class CompetitorSummaryRead(BaseModel):
    """从据点、成交和动态区域评分实时计算的同行概览。"""

    site_count: int = Field(ge=0)
    customer_count: int = Field(ge=0)
    linked_customer_count: int = Field(ge=0)
    deal_count: int = Field(ge=0)
    total_amount: Decimal
    strong_region_count: int = Field(ge=0)


class CompetitorMapItemRead(BaseModel):
    """第四地图首屏只返回同行主要据点，供全国总览绘制 Pin。"""

    id: UUID
    name: str
    website_url: str | None = None
    color: str
    description: str | None
    primary_site: CompetitorSiteRead


class CompetitorDetailRead(BaseModel):
    """点击同行后返回该同行的全部据点、成交单位、交易和强势区域。"""

    id: UUID
    name: str
    website_url: str | None = None
    color: str
    description: str | None
    summary: CompetitorSummaryRead
    sites: list[CompetitorSiteRead]
    customers: list[CompetitorCustomerRead]
    strength_regions: list[CompetitorStrengthRegionRead]


class SalesOfficeLocationRead(BaseModel):
    """公开热力图与管理端共用的销售常驻点响应字段。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    city: str
    address: str | None
    longitude: float
    latitude: float
    coverage_radius_km: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SalesOfficeLocationUpdate(BaseModel):
    """管理员可修改的销售常驻点字段；坐标与半径限制在可展示的业务范围内。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=2, max_length=160)
    city: str | None = Field(default=None, min_length=2, max_length=60)
    address: str | None = Field(default=None, max_length=500)
    longitude: float | None = Field(default=None, ge=73, le=136)
    latitude: float | None = Field(default=None, ge=3, le=54)
    coverage_radius_km: int | None = Field(default=None, ge=10, le=2000)
    is_active: bool | None = None


class PublicChannelPartnerMapPoint(BaseModel):
    """公开热力图所需的渠道点位，不返回合同、备注或尚未录入的业务坐标。"""

    id: UUID
    name: str
    partner_type: ChannelPartnerType
    address: str
    map_longitude: float
    map_latitude: float
    coverage_radius_km: int
    cooperation_level: CooperationLevel


class ChannelPartnerLocationRead(BaseModel):
    """管理员读取的完整渠道档案，包含可为空的授权、合同及备注字段。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    partner_type: ChannelPartnerType
    address: str
    longitude: float | None
    latitude: float | None
    display_longitude: float
    display_latitude: float
    authorized_coverage_area: str | None
    coverage_radius_km: int
    authorized_product_lines: list[str] | None
    cooperation_level: CooperationLevel
    contract_info: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ChannelPartnerLocationUpdate(BaseModel):
    """管理员可修改的渠道档案字段；真实与演示坐标均限制在中国地图范围内。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=2, max_length=160)
    partner_type: ChannelPartnerType | None = None
    address: str | None = Field(default=None, min_length=2, max_length=500)
    longitude: float | None = Field(default=None, ge=73, le=136)
    latitude: float | None = Field(default=None, ge=3, le=54)
    display_longitude: float | None = Field(default=None, ge=73, le=136)
    display_latitude: float | None = Field(default=None, ge=3, le=54)
    authorized_coverage_area: str | None = Field(default=None, max_length=500)
    coverage_radius_km: int | None = Field(default=None, ge=10, le=2000)
    authorized_product_lines: list[str] | None = Field(default=None, max_length=50)
    cooperation_level: CooperationLevel | None = None
    contract_info: str | None = Field(default=None, max_length=5000)
    notes: str | None = Field(default=None, max_length=5000)
    is_active: bool | None = None


class SalespersonOptionRead(BaseModel):
    """为管理员成交项目负责人下拉框提供稳定且精简的人员选项。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_code: str
    display_name: str
    is_active: bool


class FilterOptions(BaseModel):
    """提供受控筛选枚举、地点层级及管理员编辑所需的销售人员选项。"""

    organization_types: list[str]
    customer_statuses: list[str]
    review_statuses: list[str]
    provinces: list[str]
    cities: list[str]
    districts: list[str]
    salespeople: list[SalespersonOptionRead] = Field(default_factory=list)


class ReviewAction(BaseModel):
    """审核动作输入；不纳入时要求注明理由以留下可解释记录。"""

    review_status: ReviewStatus
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_exclusion_reason(self) -> "ReviewAction":
        """保证被排除的记录能够被后续复核，而非静默消失。"""

        if self.review_status is ReviewStatus.excluded and not self.note:
            raise ValueError("标记不纳入时必须填写原因")
        return self


class OrganizationBatchAction(BaseModel):
    """单次事务中的单位批量动作；动作类型决定必填字段，最多处理当前页上限 100 条。"""

    ids: list[UUID] = Field(min_length=1, max_length=100)
    action: Literal["review", "archive", "restore", "assign_owner"]
    review_status: ReviewStatus | None = None
    note: str | None = Field(default=None, max_length=2000)
    follow_up_owner: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_action_fields(self) -> "OrganizationBatchAction":
        """拒绝重复 ID 与缺失动作参数，避免批量请求产生部分或含糊更新。"""

        if len(set(self.ids)) != len(self.ids):
            raise ValueError("批量操作不能包含重复单位")
        if self.action == "review" and self.review_status is None:
            raise ValueError("批量审核必须选择审核状态")
        if self.action == "review" and self.review_status is ReviewStatus.excluded and not self.note:
            raise ValueError("批量标记不纳入时必须填写原因")
        if self.action == "assign_owner" and not self.follow_up_owner:
            raise ValueError("批量分配必须填写负责人")
        return self


class OrganizationBatchResult(BaseModel):
    """批量事务结果只返回更新数量，列表由前端按原筛选条件重新读取。"""

    updated: int = Field(ge=0)


class LoginInput(BaseModel):
    """站点授权账号登录凭据，密码仅用于本次验证。"""

    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=512)


class CurrentUserRead(BaseModel):
    """返回当前会话身份、账号范围和账号管理能力，不暴露认证凭据。"""

    username: str
    role: UserRole
    salesperson_id: UUID | None
    coverage_scopes: list["AuthorizedUserCoverageScopeRead"]
    can_manage_users: bool
    can_manage_salespeople: bool


class AuthorizedUserCoverageScopeInput(BaseModel):
    """账号新增或编辑时提交的一条四级覆盖范围。"""

    scope_level: SalesCoverageLevel
    scope_name: str = Field(min_length=1, max_length=60)
    province: str | None = Field(default=None, max_length=60)
    city: str | None = Field(default=None, max_length=60)
    amap_adcode: str | None = Field(default=None, max_length=12)

    @model_validator(mode="after")
    def normalize_scope(self) -> "AuthorizedUserCoverageScopeInput":
        """复用销售覆盖规则归一字段，拒绝层级与省市组合不一致。"""

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


class AuthorizedUserCoverageScopeRead(AuthorizedUserCoverageScopeInput):
    """账号目录返回的一条范围及其展开后的省份集合。"""

    id: UUID
    included_provinces: list[str]


class AuthorizedUserScopeCollection(BaseModel):
    """集中校验账号至少一个范围、范围去重及全国互斥规则。"""

    salesperson_id: UUID | None = None
    coverage_scopes: list[AuthorizedUserCoverageScopeInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_scope_collection(self) -> "AuthorizedUserScopeCollection":
        """禁止重复范围，并确保全国不会与其他范围并存。"""

        keys = [(item.scope_level, item.scope_name) for item in self.coverage_scopes]
        if len(keys) != len(set(keys)):
            raise ValueError("同一账号不能重复添加相同覆盖范围")
        if any(level is SalesCoverageLevel.national for level, _name in keys) and len(keys) > 1:
            raise ValueError("全国覆盖不能与其他覆盖范围同时添加")
        if not any(level is SalesCoverageLevel.national for level, _name in keys) and self.salesperson_id is None:
            raise ValueError("市、省或大区账号必须关联一名销售人员")
        return self


class AuthorizedUserCreate(AuthorizedUserScopeCollection):
    """超级管理员创建普通用户时提交凭据和至少一个覆盖范围。"""

    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    password: str = Field(min_length=12, max_length=128)


class AuthorizedUserUpdate(AuthorizedUserScopeCollection):
    """超级管理员可修改普通用户的启用状态和全部覆盖范围。"""

    is_active: bool


class AuthorizedUserRead(BaseModel):
    """授权账号列表不返回密码哈希、锁定计数或任何会话凭据。"""

    id: UUID
    username: str
    role: UserRole
    salesperson_id: UUID | None
    salesperson_name: str | None
    salesperson_employee_code: str | None
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    is_current: bool = False
    is_protected: bool = False
    coverage_scopes: list[AuthorizedUserCoverageScopeRead]


class SalespersonCoverageScopeRead(BaseModel):
    """销售地图详情中的分级负责范围，并提供范围展开后的省份集合。"""

    scope_level: str
    scope_name: str
    province: str | None
    city: str | None
    amap_adcode: str | None
    included_provinces: list[str]


class SalespersonActivitySummaryRead(BaseModel):
    """所选滚动月份内的三类活动计数，total 便于前端直接比较人效。"""

    visits: int = Field(ge=0)
    demonstrations: int = Field(ge=0)
    marketing_events: int = Field(ge=0)
    total: int = Field(ge=0)


class SalespersonPerformanceRead(BaseModel):
    """销售人员在同一时间口径下的活动、成交与储备项目汇总。"""

    period_months: int | None
    period_year: int | None = None
    activities: SalespersonActivitySummaryRead
    actual_sales_amount: Decimal = Field(ge=0)
    pipeline_amount: Decimal = Field(ge=0)
    project_count: int = Field(ge=0)
    active_opportunity_count: int = Field(ge=0)


class SalespersonCoverageRead(BaseModel):
    """销售覆盖地图完整只读项：主档、Pin 坐标、分级范围和当前期间人效。"""

    id: UUID
    employee_code: str
    display_name: str
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    coverage_center_longitude: float = Field(ge=73, le=136)
    coverage_center_latitude: float = Field(ge=3, le=54)
    coverage_scopes: list[SalespersonCoverageScopeRead]
    performance: SalespersonPerformanceRead
