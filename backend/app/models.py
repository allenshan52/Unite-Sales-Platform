"""核心数据模型：定义目标单位、地址、来源、商机、项目及审核追溯的 PostgreSQL 表。"""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrganizationType(str, enum.Enum):
    """组织分类与首期筛选规则保持一致，便于稳定筛选和统计。"""

    university = "高校"
    research_institute = "研究院"
    cdc = "疾控"
    food_drug = "食药"
    environmental = "环保"
    police = "公安"


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


class OpportunityStage(str, enum.Enum):
    """商机推进阶段，与已成交项目分表保存。"""

    identified = "已识别"
    qualifying = "资格确认"
    proposal = "方案/报价"
    negotiation = "商务谈判"
    closed_lost = "已关闭失单"


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


class AdminUser(TimestampMixin, Base):
    """首期单管理员账户；只存密码哈希，不保存明文或 token。"""

    __tablename__ = "admin_user"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sessions: Mapped[list["AdminSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AdminSession(Base):
    """服务端会话表：将浏览器 cookie 仅作为随机凭据，便于撤销和过期控制。"""

    __tablename__ = "admin_session"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user: Mapped[AdminUser] = relationship(back_populates="sessions")


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
    sites: Mapped[list["OrganizationSite"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    evidences: Mapped[list["OrganizationEvidence"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    contacts: Mapped[list["OrganizationContact"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    sales_projects: Mapped[list["SalesProject"]] = relationship(back_populates="organization", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_organization_lookup", "normalized_name", "organization_type", "review_status"),)


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

    __table_args__ = (Index("ix_site_address_deduplicate", "province", "city", "district", "address"),)


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


class Opportunity(TimestampMixin, Base):
    """仍在推进的商业机会，保存 AI 摘要、预估金额与下一步动作。"""

    __tablename__ = "opportunity"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organization.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    stage: Mapped[OpportunityStage] = mapped_column(database_enum(OpportunityStage, "opportunity_stage"), default=OpportunityStage.identified, nullable=False)
    estimated_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    ai_summary: Mapped[str | None] = mapped_column(Text)
    next_action: Mapped[str | None] = mapped_column(Text)
    next_action_at: Mapped[date | None] = mapped_column(Date)
    organization: Mapped[Organization] = relationship(back_populates="opportunities")


class SalesProject(TimestampMixin, Base):
    """已成交项目与真实成交额，独立于机会预估以确保销售统计口径准确。"""

    __tablename__ = "sales_project"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organization.id", ondelete="CASCADE"), nullable=False)
    opportunity_id: Mapped[UUID | None] = mapped_column(ForeignKey("opportunity.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contract_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    signed_at: Mapped[date | None] = mapped_column(Date)
    project_detail: Mapped[str | None] = mapped_column(Text)
    organization: Mapped[Organization] = relationship(back_populates="sales_projects")


class AuditLog(Base):
    """记录人工审核与关键编辑动作，满足名单可追溯核查的需求。"""

    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organization.id", ondelete="SET NULL"))
    actor_username: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
