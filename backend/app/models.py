"""核心数据模型：定义目标单位、客户集团、销售、典型案例及审核追溯的 PostgreSQL/PostGIS 表。"""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.sales_coverage import SalesCoverageLevel


class OrganizationType(str, enum.Enum):
    """组织分类与首期筛选规则保持一致，便于稳定筛选和统计。"""

    university = "高校"
    research_institute = "研究院"
    cdc = "疾控"
    food_drug = "食药"
    environmental = "环保"
    police = "公安"
    enterprise = "企业"


class CustomerStatus(str, enum.Enum):
    """销售关系阶段，所有新候选默认潜在客户。"""

    potential = "潜在客户"
    opportunity = "商机客户"
    won = "已成交客户"


class ReviewStatus(str, enum.Enum):
    """人工审核状态决定数据可信度，不与销售阶段混用。"""

    pending = "待核验"
    verified = "已核验"
    excluded = "不纳入"


class GeocodeStatus(str, enum.Enum):
    """地理编码结果状态，避免未确认地址生成误导性地图 pin。"""

    pending = "待编码"
    resolved = "已定位"
    low_confidence = "低置信度"
    failed = "待补地址"


class ChannelPartnerType(str, enum.Enum):
    """渠道网络的三类合作主体，用于地图开关和管理员维护。"""

    dealer = "经销商"
    agent = "代理商"
    partner = "合作伙伴"


class CooperationLevel(str, enum.Enum):
    """渠道合作等级保持为三个稳定档位，便于地图筛选与后续授权管理。"""

    level_one = "一级"
    level_two = "二级"
    level_three = "三级"


class UserRole(str, enum.Enum):
    """账号身份只区分普通用户与唯一超级管理员，区域权限由独立范围表决定。"""

    employee = "普通用户"
    admin = "超级管理员"


class OpportunityStage(str, enum.Enum):
    """商机推进阶段，与已成交项目分表保存。"""

    identified = "已识别"
    qualifying = "资格确认"
    proposal = "方案/报价"
    negotiation = "商务谈判"
    closed_lost = "已关闭失单"


class SalesActivityType(str, enum.Enum):
    """销售活动只保留需求明确的三类统计口径。"""

    visit = "拜访"
    demonstration = "演示"
    marketing_event = "市场活动"


class IntelligenceSourceType(str, enum.Enum):
    """竞争情报来源保持三个稳定类别，便于后续筛选和核验。"""

    public = "公开信息"
    frontline = "一线反馈"
    inferred = "推测"


class IntelligenceConfidence(str, enum.Enum):
    """来源置信度只表达情报可信程度，不与单位匹配可信度混用。"""

    high = "高"
    medium = "中"
    low = "低"


class CompetitorSiteType(str, enum.Enum):
    """同行据点类型用于区分总部、分部和服务点。"""

    headquarters = "总部"
    branch = "分部"
    service = "服务点"


class CompetitorStrengthLevel(str, enum.Enum):
    """同行区域强度采用三档业务口径。"""

    strong = "强"
    medium = "中"
    weak = "弱"


class CompetitorRegionLevel(str, enum.Enum):
    """强势区域首版支持省级和市级行政区。"""

    province = "省"
    city = "市"


class CompetitorCustomerLevel(str, enum.Enum):
    """同行成交单位采用一至三级分类。"""

    level_one = "一级"
    level_two = "二级"
    level_three = "三级"


class CompetitorMatchStatus(str, enum.Enum):
    """关联审核状态避免低可信匹配直接污染正式单位库。"""

    pending = "待确认"
    confirmed = "已确认"
    rejected = "已拒绝"


class EvidenceKind(str, enum.Enum):
    """可追溯纳入依据的来源类型。"""

    official_directory = "官方名录"
    department = "院系/专业目录"
    research = "研究方向/实验室"
    sports_exception = "体育例外依据"
    address = "官方地址"
    other = "其他"


def database_enum(enum_type: type[enum.Enum], name: str) -> Enum:
    """让 SQLAlchemy 绑定业务枚举的中文 value，与首版 PostgreSQL 枚举标签完全一致。"""

    return Enum(enum_type, name=name, values_callable=lambda members: [member.value for member in members])


class TimestampMixin:
    """为可维护业务表提供统一的创建、最后更新时间字段。"""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Salesperson(TimestampMixin, Base):
    """销售人员主档保存身份与地图 Pin 坐标，历史业绩均通过稳定人员 ID 关联。"""

    __tablename__ = "salesperson"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    employee_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    coverage_center_longitude: Mapped[float] = mapped_column(nullable=False)
    coverage_center_latitude: Mapped[float] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    coverage_scopes: Mapped[list["SalespersonCoverageScope"]] = relationship(back_populates="salesperson", cascade="all, delete-orphan", passive_deletes=True)
    activities: Mapped[list["SalesActivity"]] = relationship(back_populates="salesperson", passive_deletes=True)
    opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="salesperson")
    sales_projects: Mapped[list["SalesProject"]] = relationship(back_populates="salesperson")

    __table_args__ = (
        CheckConstraint("color ~ '^#[0-9A-Fa-f]{6}$'", name="ck_salesperson_color_hex"),
        CheckConstraint(
            "coverage_center_longitude BETWEEN 72.004 AND 137.8347 "
            "AND coverage_center_latitude BETWEEN 0.8293 AND 55.8271",
            name="ck_salesperson_coverage_center_gcj02_bounds",
        ),
    )


class SalespersonCoverageScope(TimestampMixin, Base):
    """销售覆盖按市、省、大区或全国逐行保存；物理表名保留以兼容历史迁移。"""

    __tablename__ = "salesperson_coverage_city"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    salesperson_id: Mapped[UUID] = mapped_column(ForeignKey("salesperson.id", ondelete="CASCADE"), nullable=False)
    scope_level: Mapped[SalesCoverageLevel] = mapped_column(database_enum(SalesCoverageLevel, "sales_coverage_level"), nullable=False)
    scope_name: Mapped[str] = mapped_column(String(60), nullable=False)
    province: Mapped[str | None] = mapped_column(String(60))
    city: Mapped[str | None] = mapped_column(String(60))
    amap_adcode: Mapped[str | None] = mapped_column(String(12))
    salesperson: Mapped[Salesperson] = relationship(back_populates="coverage_scopes")

    __table_args__ = (
        UniqueConstraint("salesperson_id", "scope_level", "scope_name", name="uq_salesperson_coverage_scope"),
        CheckConstraint("amap_adcode ~ '^[0-9]{6}$'", name="ck_salesperson_coverage_city_adcode"),
        CheckConstraint(
            "(scope_level = '市' AND province IS NOT NULL AND city IS NOT NULL AND amap_adcode IS NOT NULL) OR "
            "(scope_level = '省' AND province IS NOT NULL AND city IS NULL AND amap_adcode IS NULL) OR "
            "(scope_level IN ('大区', '全国') AND province IS NULL AND city IS NULL AND amap_adcode IS NULL)",
            name="ck_salesperson_coverage_scope_fields",
        ),
        Index("ix_salesperson_coverage_city_adcode", "amap_adcode"),
        Index("ix_salesperson_coverage_scope_level_name", "scope_level", "scope_name"),
    )


class SalesActivity(TimestampMixin, Base):
    """销售活动流水保存责任人、发生时间和城市，供滚动月份统计直接聚合。"""

    __tablename__ = "sales_activity"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    salesperson_id: Mapped[UUID] = mapped_column(ForeignKey("salesperson.id", ondelete="RESTRICT"), nullable=False)
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organization.id", ondelete="SET NULL"))
    activity_type: Mapped[SalesActivityType] = mapped_column(database_enum(SalesActivityType, "sales_activity_type"), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    province: Mapped[str] = mapped_column(String(60), nullable=False)
    city: Mapped[str] = mapped_column(String(60), nullable=False)
    amap_adcode: Mapped[str] = mapped_column(String(12), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    salesperson: Mapped[Salesperson] = relationship(back_populates="activities")
    organization: Mapped["Organization | None"] = relationship()

    __table_args__ = (
        CheckConstraint("amap_adcode ~ '^[0-9]{6}$'", name="ck_sales_activity_adcode"),
        Index("ix_sales_activity_salesperson_occurred_at", "salesperson_id", "occurred_at"),
        Index("ix_sales_activity_adcode_occurred_at", "amap_adcode", "occurred_at"),
    )


class CustomerGroup(TimestampMixin, Base):
    """独立保存客户集团主档和稳定展示颜色，不与现有目标单位表混用。"""

    __tablename__ = "customer_group"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    units: Mapped[list["CustomerGroupUnit"]] = relationship(back_populates="group", cascade="all, delete-orphan", passive_deletes=True)

    __table_args__ = (CheckConstraint("color ~ '^#[0-9A-Fa-f]{6}$'", name="ck_customer_group_color_hex"),)


class CustomerGroupUnit(TimestampMixin, Base):
    """保存集团总部和任意层级分支；金额口径、地图坐标与现有销售数据保持隔离。"""

    __tablename__ = "customer_group_unit"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    group_id: Mapped[UUID] = mapped_column(ForeignKey("customer_group.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("customer_group_unit.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_headquarters: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    province: Mapped[str] = mapped_column(String(60), nullable=False)
    city: Mapped[str] = mapped_column(String(60), nullable=False)
    # 高德展示继续使用 GCJ-02；PostGIS location 单独保存转换后的 WGS84。
    longitude: Mapped[float] = mapped_column(nullable=False)
    latitude: Mapped[float] = mapped_column(nullable=False)
    location: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326, spatial_index=True), nullable=False)
    is_won: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    actual_sales_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal(0), nullable=False)
    opportunity_stage: Mapped[OpportunityStage | None] = mapped_column(database_enum(OpportunityStage, "opportunity_stage"))
    estimated_opportunity_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    group: Mapped[CustomerGroup] = relationship(back_populates="units")
    parent: Mapped["CustomerGroupUnit | None"] = relationship(remote_side="CustomerGroupUnit.id", back_populates="children", foreign_keys=[parent_id])
    children: Mapped[list["CustomerGroupUnit"]] = relationship(back_populates="parent", foreign_keys=[parent_id], passive_deletes=True)

    __table_args__ = (
        UniqueConstraint("group_id", "name", name="uq_customer_group_unit_name"),
        CheckConstraint(
            "(is_headquarters AND parent_id IS NULL) OR (NOT is_headquarters AND parent_id IS NOT NULL)",
            name="ck_customer_group_unit_tree_role",
        ),
        CheckConstraint(
            "(is_won AND actual_sales_amount > 0) OR (NOT is_won AND actual_sales_amount = 0)",
            name="ck_customer_group_unit_deal_amount",
        ),
        CheckConstraint("estimated_opportunity_amount IS NULL OR estimated_opportunity_amount >= 0", name="ck_customer_group_unit_estimated_amount"),
        CheckConstraint("longitude BETWEEN 72.004 AND 137.8347 AND latitude BETWEEN 0.8293 AND 55.8271", name="ck_customer_group_unit_gcj02_bounds"),
        Index("ix_customer_group_unit_group_id", "group_id"),
        Index("ix_customer_group_unit_province_city", "province", "city"),
        Index("uq_customer_group_single_headquarters", "group_id", unique=True, postgresql_where=text("is_headquarters")),
    )


class AdminUser(TimestampMixin, Base):
    """站点授权账号；密码、身份与区域范围分离保存，不保存明文或 token。"""

    __tablename__ = "admin_user"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    salesperson_id: Mapped[UUID | None] = mapped_column(ForeignKey("salesperson.id", ondelete="SET NULL"))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(String(20), default=UserRole.employee, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sessions: Mapped[list["AdminSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    coverage_scopes: Mapped[list["AdminUserCoverageScope"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    salesperson: Mapped["Salesperson | None"] = relationship()

    __table_args__ = (
        CheckConstraint("role IN ('普通用户', '超级管理员')", name="ck_admin_user_role"),
        Index("ix_admin_user_salesperson_id", "salesperson_id"),
    )


class AdminUserCoverageScope(TimestampMixin, Base):
    """账号数据权限按市、省、大区或全国逐行保存，支持一个账号负责多个区域。"""

    __tablename__ = "admin_user_coverage_scope"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id", ondelete="CASCADE"), nullable=False)
    scope_level: Mapped[SalesCoverageLevel] = mapped_column(database_enum(SalesCoverageLevel, "sales_coverage_level"), nullable=False)
    scope_name: Mapped[str] = mapped_column(String(60), nullable=False)
    province: Mapped[str | None] = mapped_column(String(60))
    city: Mapped[str | None] = mapped_column(String(60))
    amap_adcode: Mapped[str | None] = mapped_column(String(12))
    user: Mapped[AdminUser] = relationship(back_populates="coverage_scopes")

    __table_args__ = (
        UniqueConstraint("user_id", "scope_level", "scope_name", name="uq_admin_user_coverage_scope"),
        CheckConstraint("amap_adcode ~ '^[0-9]{6}$'", name="ck_admin_user_coverage_scope_adcode"),
        CheckConstraint(
            "(scope_level = '市' AND province IS NOT NULL AND city IS NOT NULL AND amap_adcode IS NOT NULL) OR "
            "(scope_level = '省' AND province IS NOT NULL AND city IS NULL AND amap_adcode IS NULL) OR "
            "(scope_level IN ('大区', '全国') AND province IS NULL AND city IS NULL AND amap_adcode IS NULL)",
            name="ck_admin_user_coverage_scope_fields",
        ),
        Index("ix_admin_user_coverage_scope_user", "user_id"),
        Index("ix_admin_user_coverage_scope_level_name", "scope_level", "scope_name"),
    )


class AdminSession(Base):
    """服务端会话表：将浏览器 cookie 仅作为随机凭据，便于撤销和过期控制。"""

    __tablename__ = "admin_session"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user: Mapped[AdminUser] = relationship(back_populates="sessions")

    __table_args__ = (Index("ix_admin_session_expires_at", "expires_at"),)


class Organization(TimestampMixin, Base):
    """目标单位主档案，保存可长期筛选、审核和销售管理的稳定字段。"""

    __tablename__ = "organization"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_type: Mapped[OrganizationType] = mapped_column(database_enum(OrganizationType, "organization_type"), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(120))
    customer_status: Mapped[CustomerStatus] = mapped_column(database_enum(CustomerStatus, "customer_status"), default=CustomerStatus.potential, nullable=False)
    review_status: Mapped[ReviewStatus] = mapped_column(database_enum(ReviewStatus, "review_status"), default=ReviewStatus.pending, nullable=False)
    inclusion_reason: Mapped[str | None] = mapped_column(Text)
    is_sports_exception: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parent_group: Mapped[str | None] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(500))
    unified_social_credit_code: Mapped[str | None] = mapped_column(String(18), unique=True)
    recent_follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recent_follow_up_content: Mapped[str | None] = mapped_column(Text)
    follow_up_owner: Mapped[str | None] = mapped_column(String(120))
    cooperation_intent: Mapped[str | None] = mapped_column(String(500))
    cooperation_level: Mapped[CooperationLevel | None] = mapped_column(database_enum(CooperationLevel, "cooperation_level"))
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sites: Mapped[list["OrganizationSite"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    evidences: Mapped[list["OrganizationEvidence"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    contacts: Mapped[list["OrganizationContact"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    sales_projects: Mapped[list["SalesProject"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    competitor_links: Mapped[list["CompetitorCustomerOrganizationLink"]] = relationship(back_populates="organization", passive_deletes=True)

    __table_args__ = (
        Index("uq_organization_normalized_name", "normalized_name", unique=True),
        Index("ix_organization_lookup", "normalized_name", "organization_type", "review_status"),
        Index("ix_organization_updated_at_id", "updated_at", "id"),
        Index("ix_organization_archived_at", "archived_at"),
    )
    __mapper_args__ = {"version_id_col": version}


class OrganizationSite(TimestampMixin, Base):
    """单位地点与地理编码结果；一个单位可拥有总部、分校区或实验室多个地点。"""

    __tablename__ = "organization_site"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organization.id", ondelete="CASCADE"), nullable=False)
    site_name: Mapped[str | None] = mapped_column(String(160))
    raw_address: Mapped[str | None] = mapped_column(String(500))
    address: Mapped[str | None] = mapped_column(String(500))
    province: Mapped[str | None] = mapped_column(String(60), index=True)
    city: Mapped[str | None] = mapped_column(String(60), index=True)
    district: Mapped[str | None] = mapped_column(String(80), index=True)
    amap_adcode: Mapped[str | None] = mapped_column(String(12))
    geocode_status: Mapped[GeocodeStatus] = mapped_column(database_enum(GeocodeStatus, "geocode_status"), default=GeocodeStatus.pending, nullable=False)
    geocode_confidence: Mapped[int | None] = mapped_column(Integer)
    # 高德地理编码坐标（GCJ-02）；管理后台直接将其传给 AMap JSAPI 和 MarkerCluster。
    longitude: Mapped[float | None] = mapped_column()
    latitude: Mapped[float | None] = mapped_column()
    # 同一地点转换后的 WGS84 坐标，供 PostGIS 的 SRID 4326 空间查询使用。
    location: Mapped[Any | None] = mapped_column(Geometry("POINT", srid=4326, spatial_index=True))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    organization: Mapped[Organization] = relationship(back_populates="sites")

    __table_args__ = (
        Index("ix_organization_site_organization_id", "organization_id"),
        Index("uq_organization_site_primary", "organization_id", unique=True, postgresql_where=text("is_primary")),
        Index("ix_site_address_deduplicate", "province", "city", "district", "address"),
    )


class Competitor(TimestampMixin, Base):
    """同行主档保存名称、官网和地图颜色，业务明细始终留在独立表中。"""

    __tablename__ = "competitor"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    website_url: Mapped[str | None] = mapped_column(String(1000))
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sites: Mapped[list["CompetitorSite"]] = relationship(back_populates="competitor", cascade="all, delete-orphan", passive_deletes=True)
    customers: Mapped[list["CompetitorCustomer"]] = relationship(back_populates="competitor", cascade="all, delete-orphan", passive_deletes=True)
    strength_regions: Mapped[list["CompetitorStrengthRegion"]] = relationship(back_populates="competitor", cascade="all, delete-orphan", passive_deletes=True)

    __table_args__ = (CheckConstraint("color ~ '^#[0-9A-Fa-f]{6}$'", name="ck_competitor_color_hex"),)


class CompetitorSite(TimestampMixin, Base):
    """同行总部、分部和服务点使用 GCJ-02 坐标，并保留来源与置信度。"""

    __tablename__ = "competitor_site"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    competitor_id: Mapped[UUID] = mapped_column(ForeignKey("competitor.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    site_type: Mapped[CompetitorSiteType] = mapped_column(database_enum(CompetitorSiteType, "competitor_site_type"), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    province: Mapped[str] = mapped_column(String(60), nullable=False)
    city: Mapped[str] = mapped_column(String(60), nullable=False)
    longitude: Mapped[float] = mapped_column(nullable=False)
    latitude: Mapped[float] = mapped_column(nullable=False)
    source_type: Mapped[IntelligenceSourceType] = mapped_column(database_enum(IntelligenceSourceType, "intelligence_source_type"), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    confidence: Mapped[IntelligenceConfidence] = mapped_column(database_enum(IntelligenceConfidence, "intelligence_confidence"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    competitor: Mapped[Competitor] = relationship(back_populates="sites")

    __table_args__ = (
        UniqueConstraint("competitor_id", "name", name="uq_competitor_site_name"),
        CheckConstraint("longitude BETWEEN 72.004 AND 137.8347 AND latitude BETWEEN 0.8293 AND 55.8271", name="ck_competitor_site_gcj02_bounds"),
        Index("ix_competitor_site_competitor_id", "competitor_id"),
        Index("uq_competitor_single_primary_site", "competitor_id", unique=True, postgresql_where=text("is_primary")),
    )


class CompetitorCustomer(TimestampMixin, Base):
    """同行成交单位保存原始竞争情报，不要求必须匹配现有正式单位。"""

    __tablename__ = "competitor_customer"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    competitor_id: Mapped[UUID] = mapped_column(ForeignKey("competitor.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_level: Mapped[CompetitorCustomerLevel] = mapped_column(database_enum(CompetitorCustomerLevel, "competitor_customer_level"), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    province: Mapped[str] = mapped_column(String(60), nullable=False)
    city: Mapped[str] = mapped_column(String(60), nullable=False)
    longitude: Mapped[float] = mapped_column(nullable=False)
    latitude: Mapped[float] = mapped_column(nullable=False)
    source_type: Mapped[IntelligenceSourceType] = mapped_column(database_enum(IntelligenceSourceType, "intelligence_source_type"), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    confidence: Mapped[IntelligenceConfidence] = mapped_column(database_enum(IntelligenceConfidence, "intelligence_confidence"), nullable=False)
    first_observed_at: Mapped[date | None] = mapped_column(Date)
    last_verified_at: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    competitor: Mapped[Competitor] = relationship(back_populates="customers")
    deals: Mapped[list["CompetitorDeal"]] = relationship(back_populates="customer", cascade="all, delete-orphan", passive_deletes=True)
    organization_link: Mapped["CompetitorCustomerOrganizationLink | None"] = relationship(back_populates="competitor_customer", passive_deletes=True)

    __table_args__ = (
        UniqueConstraint("competitor_id", "name", name="uq_competitor_customer_name"),
        CheckConstraint("longitude BETWEEN 72.004 AND 137.8347 AND latitude BETWEEN 0.8293 AND 55.8271", name="ck_competitor_customer_gcj02_bounds"),
        Index("ix_competitor_customer_competitor_id", "competitor_id"),
    )


class CompetitorDeal(TimestampMixin, Base):
    """同行成交记录保存项目、产品、数量、供应商、金额和来源，允许同一单位出现多笔交易。"""

    __tablename__ = "competitor_deal"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    competitor_customer_id: Mapped[UUID] = mapped_column(ForeignKey("competitor_customer.id", ondelete="CASCADE"), nullable=False)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    deal_type: Mapped[str] = mapped_column(String(80), nullable=False)
    product_name: Mapped[str | None] = mapped_column(String(255))
    specification_model: Mapped[str | None] = mapped_column(String(255))
    product_image_url: Mapped[str | None] = mapped_column(String(1000))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    supplier_name: Mapped[str | None] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    signed_at: Mapped[date | None] = mapped_column(Date)
    source_type: Mapped[IntelligenceSourceType] = mapped_column(database_enum(IntelligenceSourceType, "intelligence_source_type"), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    confidence: Mapped[IntelligenceConfidence] = mapped_column(database_enum(IntelligenceConfidence, "intelligence_confidence"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    customer: Mapped[CompetitorCustomer] = relationship(back_populates="deals")
    products: Mapped[list["CompetitorDealProduct"]] = relationship(
        back_populates="deal",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="CompetitorDealProduct.position",
    )

    __table_args__ = (
        CheckConstraint("unit_price IS NULL OR unit_price > 0", name="ck_competitor_deal_positive_unit_price"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_competitor_deal_positive_quantity"),
        CheckConstraint("amount > 0", name="ck_competitor_deal_positive_amount"),
        Index("ix_competitor_deal_customer_id", "competitor_customer_id"),
    )


class CompetitorDealProduct(TimestampMixin, Base):
    """保存同行成交订单中的单条产品、品牌、规格、数量和分项金额。"""

    __tablename__ = "competitor_deal_product"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    competitor_deal_id: Mapped[UUID] = mapped_column(ForeignKey("competitor_deal.id", ondelete="CASCADE"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255))
    specification_model: Mapped[str | None] = mapped_column(String(255))
    product_image_url: Mapped[str | None] = mapped_column(String(1000))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deal: Mapped[CompetitorDeal] = relationship(back_populates="products")

    __table_args__ = (
        CheckConstraint("unit_price IS NULL OR unit_price > 0", name="ck_competitor_deal_product_unit_price_positive"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_competitor_deal_product_quantity_positive"),
        CheckConstraint("line_total >= 0", name="ck_competitor_deal_product_line_total_nonnegative"),
        UniqueConstraint("competitor_deal_id", "position", name="uq_competitor_deal_product_position", deferrable=True, initially="DEFERRED"),
        Index("ix_competitor_deal_product_competitor_deal_id", "competitor_deal_id"),
    )


class CompetitorStrengthRegion(TimestampMixin, Base):
    """同行强势区域保存行政区级别、强度及判断依据，地图按名称查询边界。"""

    __tablename__ = "competitor_strength_region"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    competitor_id: Mapped[UUID] = mapped_column(ForeignKey("competitor.id", ondelete="CASCADE"), nullable=False)
    region_level: Mapped[CompetitorRegionLevel] = mapped_column(database_enum(CompetitorRegionLevel, "competitor_region_level"), nullable=False)
    province: Mapped[str] = mapped_column(String(60), nullable=False)
    city: Mapped[str | None] = mapped_column(String(60))
    strength_level: Mapped[CompetitorStrengthLevel] = mapped_column(database_enum(CompetitorStrengthLevel, "competitor_strength_level"), nullable=False)
    source_type: Mapped[IntelligenceSourceType] = mapped_column(database_enum(IntelligenceSourceType, "intelligence_source_type"), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    confidence: Mapped[IntelligenceConfidence] = mapped_column(database_enum(IntelligenceConfidence, "intelligence_confidence"), nullable=False)
    basis: Mapped[str] = mapped_column(Text, nullable=False)
    competitor: Mapped[Competitor] = relationship(back_populates="strength_regions")

    __table_args__ = (
        UniqueConstraint("competitor_id", "province", "city", name="uq_competitor_strength_region"),
        CheckConstraint("(region_level = '省' AND city IS NULL) OR (region_level = '市' AND city IS NOT NULL)", name="ck_competitor_strength_region_scope"),
        Index("ix_competitor_strength_region_competitor_id", "competitor_id"),
    )


class CompetitorCustomerOrganizationLink(TimestampMixin, Base):
    """把同行成交单位映射到正式 organization，并独立记录匹配审核信息。"""

    __tablename__ = "competitor_customer_organization_link"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    competitor_customer_id: Mapped[UUID] = mapped_column(ForeignKey("competitor_customer.id", ondelete="CASCADE"), nullable=False, unique=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organization.id", ondelete="CASCADE"), nullable=False)
    match_status: Mapped[CompetitorMatchStatus] = mapped_column(database_enum(CompetitorMatchStatus, "competitor_match_status"), nullable=False)
    match_method: Mapped[str] = mapped_column(String(120), nullable=False)
    match_confidence: Mapped[IntelligenceConfidence] = mapped_column(database_enum(IntelligenceConfidence, "intelligence_confidence"), nullable=False)
    matched_by: Mapped[str | None] = mapped_column(String(120))
    matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    competitor_customer: Mapped[CompetitorCustomer] = relationship(back_populates="organization_link")
    organization: Mapped[Organization] = relationship(back_populates="competitor_links")

    __table_args__ = (Index("ix_competitor_link_organization_id", "organization_id"),)


class SalesOfficeLocation(TimestampMixin, Base):
    """销售办公地点或常驻点；坐标和覆盖半径由管理员维护并供公开热力图叠加展示。"""

    __tablename__ = "sales_office_location"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    city: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(String(500))
    # 常驻点使用 GCJ-02 坐标；覆盖半径以公里保存，避免把视图像素写入业务数据。
    longitude: Mapped[float] = mapped_column(nullable=False)
    latitude: Mapped[float] = mapped_column(nullable=False)
    coverage_radius_km: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ChannelPartnerLocation(TimestampMixin, Base):
    """经销商、代理商与合作伙伴档案；敏感合同和备注仅供管理端维护。"""

    __tablename__ = "channel_partner_location"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    partner_type: Mapped[ChannelPartnerType] = mapped_column(database_enum(ChannelPartnerType, "channel_partner_type"), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    # 真实业务坐标允许暂空；演示地图中心坐标独立保存，未来录入真实坐标后优先使用真实值。
    longitude: Mapped[float | None] = mapped_column()
    latitude: Mapped[float | None] = mapped_column()
    display_longitude: Mapped[float] = mapped_column(nullable=False)
    display_latitude: Mapped[float] = mapped_column(nullable=False)
    authorized_coverage_area: Mapped[str | None] = mapped_column(String(500))
    coverage_radius_km: Mapped[int] = mapped_column(Integer, nullable=False)
    authorized_product_lines: Mapped[list[str] | None] = mapped_column(JSONB)
    cooperation_level: Mapped[CooperationLevel] = mapped_column(database_enum(CooperationLevel, "cooperation_level"), nullable=False, index=True)
    contract_info: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class OrganizationEvidence(Base):
    """官方来源和专业/研究方向证据，保证高校与研究院可追溯地纳入。"""

    __tablename__ = "organization_evidence"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organization.id", ondelete="CASCADE"), nullable=False)
    evidence_kind: Mapped[EvidenceKind] = mapped_column(database_enum(EvidenceKind, "evidence_kind"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    published_at: Mapped[date | None] = mapped_column(Date)
    retrieved_at: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text)
    organization: Mapped[Organization] = relationship(back_populates="evidences")

    __table_args__ = (Index("ix_organization_evidence_organization_id", "organization_id"),)


class ImportBatch(TimestampMixin, Base):
    """一次可回溯的名单导入批次，记录来源范围与结果统计。"""

    __tablename__ = "import_batch"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_scope: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    geocode_failed_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    rows: Mapped[list["ImportRow"]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class ImportRow(Base):
    """保留导入原始行与去重判定，支持发现规则变更后的重新处理。"""

    __tablename__ = "import_row"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("import_batch.id", ondelete="CASCADE"), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    normalized_name: Mapped[str | None] = mapped_column(String(255))
    processing_status: Mapped[str] = mapped_column(String(50), default="待处理", nullable=False)
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organization.id", ondelete="SET NULL"))
    batch: Mapped[ImportBatch] = relationship(back_populates="rows")


class DuplicateCandidate(Base):
    """候选重复项仅供人工合并，绝不自动覆盖已核验的单位档案。"""

    __tablename__ = "duplicate_candidate"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    primary_organization_id: Mapped[UUID] = mapped_column(ForeignKey("organization.id", ondelete="CASCADE"), nullable=False)
    candidate_organization_id: Mapped[UUID] = mapped_column(ForeignKey("organization.id", ondelete="CASCADE"), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("primary_organization_id", "candidate_organization_id", name="uq_duplicate_pair"),)


class OrganizationContact(TimestampMixin, Base):
    """受权限保护的联系人预留表；字段已建但不在普通列表返回。"""

    __tablename__ = "organization_contact"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organization.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    department: Mapped[str | None] = mapped_column(String(160))
    title: Mapped[str | None] = mapped_column(String(160))
    mobile: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(254))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    organization: Mapped[Organization] = relationship(back_populates="contacts")

    __table_args__ = (Index("ix_organization_contact_organization_id", "organization_id"),)


class Opportunity(TimestampMixin, Base):
    """仍在推进的商业机会，保存 AI 摘要、预估金额与下一步动作。"""

    __tablename__ = "opportunity"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organization.id", ondelete="CASCADE"), nullable=False)
    salesperson_id: Mapped[UUID | None] = mapped_column(ForeignKey("salesperson.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    stage: Mapped[OpportunityStage] = mapped_column(database_enum(OpportunityStage, "opportunity_stage"), default=OpportunityStage.identified, nullable=False)
    estimated_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    ai_summary: Mapped[str | None] = mapped_column(Text)
    next_action: Mapped[str | None] = mapped_column(Text)
    next_action_at: Mapped[date | None] = mapped_column(Date)
    organization: Mapped[Organization] = relationship(back_populates="opportunities")
    salesperson: Mapped[Salesperson | None] = relationship(back_populates="opportunities")

    __table_args__ = (
        CheckConstraint("estimated_amount IS NULL OR estimated_amount >= 0", name="ck_opportunity_estimated_amount_nonnegative"),
        Index("ix_opportunity_organization_id", "organization_id"),
        Index("ix_opportunity_salesperson_stage", "salesperson_id", "stage"),
    )


class SalesProject(TimestampMixin, Base):
    """保存优纳特实际成交项目及产品、供应商和成交所在地明细。"""

    __tablename__ = "sales_project"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organization.id", ondelete="CASCADE"), nullable=False)
    opportunity_id: Mapped[UUID | None] = mapped_column(ForeignKey("opportunity.id", ondelete="SET NULL"))
    salesperson_id: Mapped[UUID | None] = mapped_column(ForeignKey("salesperson.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contract_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    supplier_name: Mapped[str | None] = mapped_column(String(255))
    specification_model: Mapped[str | None] = mapped_column(String(255))
    province: Mapped[str | None] = mapped_column(String(60))
    city: Mapped[str | None] = mapped_column(String(60))
    signed_at: Mapped[date | None] = mapped_column(Date)
    project_detail: Mapped[str | None] = mapped_column(Text)
    organization: Mapped[Organization] = relationship(back_populates="sales_projects")
    salesperson: Mapped[Salesperson | None] = relationship(back_populates="sales_projects")
    products: Mapped[list["SalesProjectProduct"]] = relationship(
        back_populates="sales_project",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="SalesProjectProduct.position",
    )
    typical_cases: Mapped[list["TypicalCase"]] = relationship(back_populates="sales_project", passive_deletes=True)

    __table_args__ = (
        CheckConstraint("contract_amount >= 0", name="ck_sales_project_contract_amount_nonnegative"),
        CheckConstraint("unit_price IS NULL OR unit_price > 0", name="ck_sales_project_unit_price_positive"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_sales_project_quantity_positive"),
        Index("ix_sales_project_organization_id", "organization_id"),
        Index("ix_sales_project_signed_at", "signed_at"),
        Index("ix_sales_project_salesperson_signed_at", "salesperson_id", "signed_at"),
    )


class SalesProjectProduct(TimestampMixin, Base):
    """保存优纳特成交项目中的单条产品、品牌、规格、数量和分项金额。"""

    __tablename__ = "sales_project_product"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    sales_project_id: Mapped[UUID] = mapped_column(ForeignKey("sales_project.id", ondelete="CASCADE"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255))
    specification_model: Mapped[str | None] = mapped_column(String(255))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sales_project: Mapped[SalesProject] = relationship(back_populates="products")

    __table_args__ = (
        CheckConstraint("unit_price IS NULL OR unit_price > 0", name="ck_sales_project_product_unit_price_positive"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_sales_project_product_quantity_positive"),
        CheckConstraint("line_total >= 0", name="ck_sales_project_product_line_total_nonnegative"),
        UniqueConstraint("sales_project_id", "position", name="uq_sales_project_product_position", deferrable=True, initially="DEFERRED"),
        Index("ix_sales_project_product_sales_project_id", "sales_project_id"),
    )


class TypicalCase(TimestampMixin, Base):
    """保存按省发布的去敏案例故事；真实成交口径继续引用销售项目。"""

    __tablename__ = "typical_case"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    sales_project_id: Mapped[UUID | None] = mapped_column(ForeignKey("sales_project.id", ondelete="SET NULL"))
    province: Mapped[str] = mapped_column(String(60), nullable=False)
    province_adcode: Mapped[str] = mapped_column(String(6), nullable=False)
    city: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(240))
    customer_display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    industry_label: Mapped[str] = mapped_column(String(120), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    challenge: Mapped[str] = mapped_column(Text, nullable=False)
    solution: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    product_scope: Mapped[str] = mapped_column(Text, nullable=False)
    customer_quote: Mapped[str | None] = mapped_column(Text)
    quote_attribution: Mapped[str | None] = mapped_column(String(160))
    show_contract_amount: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    images: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    metrics: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    sales_project: Mapped[SalesProject | None] = relationship(back_populates="typical_cases")

    __table_args__ = (
        CheckConstraint("province_adcode ~ '^[0-9]{6}$'", name="ck_typical_case_province_adcode"),
        CheckConstraint("NOT is_featured OR is_published", name="ck_typical_case_featured_published"),
        Index("ix_typical_case_project", "sales_project_id"),
        Index("uq_typical_case_province", "province", unique=True),
        Index(
            "uq_typical_case_project",
            "sales_project_id",
            unique=True,
            postgresql_where=text("sales_project_id IS NOT NULL"),
        ),
        Index("uq_typical_case_featured", "is_featured", unique=True, postgresql_where=text("is_featured")),
    )


class AuditLog(Base):
    """记录人工审核与关键编辑动作，满足名单可追溯核查的需求。"""

    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organization.id", ondelete="SET NULL"))
    actor_username: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
