"""成交订单后台的筛选、分页、订单级写入和多产品明细响应模型。"""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.admin_data_schemas import CompetitorDealProductAdminInput
from app.models import IntelligenceConfidence, IntelligenceSourceType


class AdminUniteDealProductInput(BaseModel):
    """定义优纳特订单级表单提交的一条产品明细。"""

    id: UUID | None = None
    product_name: str = Field(min_length=1, max_length=255)
    brand: str | None = Field(default=None, max_length=255)
    specification_model: str | None = Field(default=None, max_length=255)
    unit_price: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=3)
    line_total: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


class AdminUniteDealInput(BaseModel):
    """定义成交订单页可独立新增或修改的优纳特订单全部字段。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    organization_id: UUID | None = None
    organization_name: str | None = Field(default=None, min_length=2, max_length=255)
    opportunity_id: UUID | None = None
    salesperson_id: UUID | None = None
    project_name: str = Field(min_length=1, max_length=255)
    total_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    supplier_name: str | None = Field(default=None, max_length=255)
    location_name: str | None = Field(default=None, max_length=255)
    province: str | None = Field(default=None, max_length=60)
    city: str | None = Field(default=None, max_length=60)
    signed_at: date | None = None
    notes: str | None = Field(default=None, max_length=5000)
    products: list[AdminUniteDealProductInput] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_organization_reference(self) -> "AdminUniteDealInput":
        """校验成交单位引用及高德所在地名称与省市的完整性。"""

        if self.organization_id is None and self.organization_name is None:
            raise ValueError("请选择或输入成交单位")
        if bool(self.province) != bool(self.city):
            raise ValueError("成交单位所在地的省份和城市必须同时填写")
        if self.location_name and (not self.province or not self.city):
            raise ValueError("成交单位所在地必须同时包含省份和城市")
        return self


class AdminCompetitorDealInput(BaseModel):
    """定义同行订单及两个独立业务主体，支持按名称自动建立待审核主档。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    competitor_id: UUID | None = None
    competitor_name: str | None = Field(default=None, min_length=2, max_length=255)
    organization_id: UUID | None = None
    organization_name: str | None = Field(default=None, min_length=2, max_length=255)
    project_name: str = Field(min_length=2, max_length=255)
    deal_type: str | None = Field(default=None, min_length=1, max_length=80)
    products: list[CompetitorDealProductAdminInput] = Field(default_factory=list, max_length=100)
    supplier_name: str | None = Field(default=None, max_length=255)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    signed_at: date | None = None
    location_name: str | None = Field(default=None, max_length=255)
    province: str | None = Field(default=None, max_length=60)
    city: str | None = Field(default=None, max_length=60)
    source_type: IntelligenceSourceType | None = None
    source_reference: str | None = Field(default=None, min_length=2, max_length=500)
    source_url: str | None = Field(default=None, max_length=1000)
    confidence: IntelligenceConfidence | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def validate_parties(self) -> "AdminCompetitorDealInput":
        """校验同行、成交单位引用及高德所在地名称与省市的完整性。"""

        if self.competitor_id is None and self.competitor_name is None:
            raise ValueError("请选择或输入成交同行")
        if self.organization_id is None and self.organization_name is None:
            raise ValueError("请选择或输入成交单位")
        if bool(self.province) != bool(self.city):
            raise ValueError("成交单位所在地的省份和城市必须同时填写")
        if self.location_name and (not self.province or not self.city):
            raise ValueError("成交单位所在地必须同时包含省份和城市")
        return self


class AdminDealMutationResult(BaseModel):
    """返回订单级写操作生成或保留的记录 ID。"""

    id: UUID


class AdminDealProductRead(BaseModel):
    """统一优纳特与同行订单的产品品牌明细显示字段。"""

    id: UUID
    product_name: str
    brand: str | None = None
    specification_model: str | None = None
    product_image_url: str | None = None
    unit_price: Decimal | None = None
    quantity: Decimal | None = None
    line_total: Decimal = Field(ge=0)


class AdminDealListItem(BaseModel):
    """统一成交订单列表行，同时保留不同卖方特有的信息。"""

    id: UUID
    seller_type: Literal["unite", "competitor"]
    seller_id: UUID | None = None
    customer_id: UUID
    organization_id: UUID | None = None
    seller_name: str
    customer_name: str
    project_name: str
    total_amount: Decimal = Field(ge=0)
    supplier_name: str | None = None
    opportunity_id: UUID | None = None
    salesperson_id: UUID | None = None
    salesperson_name: str | None = None
    signed_at: date | None = None
    location_name: str | None = None
    province: str | None = None
    city: str | None = None
    deal_type: str | None = None
    source_type: IntelligenceSourceType | None = None
    source_reference: str | None = None
    source_url: str | None = None
    confidence: IntelligenceConfidence | None = None
    notes: str | None = None
    products: list[AdminDealProductRead] = Field(default_factory=list)


class AdminDealPage(BaseModel):
    """返回后台成交订单的统一分页结果。"""

    items: list[AdminDealListItem]
    total: int
    page: int
    page_size: int


class AdminDealOption(BaseModel):
    """提供同行、供应商等筛选器的值与显示名称。"""

    value: str
    label: str


class AdminDealFilterOptions(BaseModel):
    """一次返回成交订单页面初始化所需的稳定筛选选项。"""

    competitors: list[AdminDealOption]
    suppliers: list[str]
    years: list[int]
