"""API 数据模式：通过 Pydantic 分隔公开目录字段与管理员单位详情。"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.models import ChannelPartnerType, CooperationLevel, CustomerStatus, EvidenceKind, GeocodeStatus, OpportunityStage, OrganizationType, ReviewStatus


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


class SalesProjectUpdate(BaseModel):
    """管理员在单位编辑页维护的一条已成交项目和实际合同金额。"""

    id: UUID | None = None
    opportunity_id: UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    contract_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    signed_at: date | None = None
    project_detail: str | None = Field(default=None, max_length=5000)


class OrganizationUpdate(BaseModel):
    """管理员原子编辑单位主档、主地点及联系人、成交项目和商机集合；证据与审计保持独立。"""

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


class SalesProjectRead(SalesProjectUpdate):
    """管理员单位详情返回的成交项目记录。"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID


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


class PublicOrganizationPage(BaseModel):
    """公开单位目录的分页响应，只承载主站允许显示的数据。"""

    items: list[PublicOrganizationRead]
    total: int
    page: int
    page_size: int


class ProvinceOrganizationSummary(BaseModel):
    """省级单位热力聚合结果，提供总量及类型、客户状态拆分。"""

    province: str
    total: int
    organization_types: dict[str, int]
    customer_statuses: dict[str, int]


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


class FilterOptions(BaseModel):
    """前端筛选器的受控枚举与省市区层级，避免浏览器自行扫描业务记录。"""

    organization_types: list[str]
    customer_statuses: list[str]
    review_statuses: list[str]
    provinces: list[str]
    cities: list[str]
    districts: list[str]


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


class LoginInput(BaseModel):
    """管理员登录凭据，密码仅用于本次验证。"""

    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=512)


class CurrentUserRead(BaseModel):
    """返回当前会话身份而不暴露任何认证凭据。"""

    username: str
