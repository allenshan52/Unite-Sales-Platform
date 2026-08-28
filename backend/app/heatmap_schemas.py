"""成交金额热力图 API 合同：统一优纳特、同行与采购意向的省级汇总和逐笔详情。"""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import IntelligenceConfidence, IntelligenceSourceType, OpportunityStage


class DealHeatmapSellerRead(BaseModel):
    """热力图可选卖方；同行额外返回公司官网供逐笔详情展示。"""

    id: str
    name: str
    kind: Literal["unite", "competitor"]
    website_url: str | None = None


class DealHeatmapProvinceRead(BaseModel):
    """单省实际成交与优纳特未成交意向保持独立金额口径。"""

    province: str
    signed_amount: Decimal = Field(ge=0)
    signed_order_count: int = Field(ge=0)
    intention_amount: Decimal = Field(ge=0)
    intention_count: int = Field(ge=0)


class DealHeatmapSummaryRead(BaseModel):
    """返回当前卖方、可选成交年份与有成交或意向数据的省份。"""

    seller: DealHeatmapSellerRead
    available_years: list[int]
    provinces: list[DealHeatmapProvinceRead]


class DealHeatmapProductRead(BaseModel):
    """返回热力图订单中的一条产品品牌明细。"""

    id: UUID
    product_name: str
    brand: str | None = None
    specification_model: str | None = None
    product_image_url: str | None = None
    unit_price: Decimal | None = Field(default=None, gt=0)
    quantity: Decimal | None = Field(default=None, gt=0)
    line_total: Decimal = Field(ge=0)


class DealHeatmapOrderRead(BaseModel):
    """逐笔成交统一核心字段；同行额外返回客户位置、产品、来源与备注。"""

    id: UUID
    customer_name: str
    customer_province: str | None = None
    customer_city: str | None = None
    project_name: str
    amount: Decimal = Field(ge=0)
    signed_at: date | None
    deal_type: str | None = None
    products: list[DealHeatmapProductRead] = Field(default_factory=list)
    product_name: str | None = None
    specification_model: str | None = None
    product_image_url: str | None = None
    unit_price: Decimal | None = Field(default=None, gt=0)
    quantity: Decimal | None = Field(default=None, gt=0)
    supplier_name: str | None = None
    source_type: IntelligenceSourceType | None = None
    source_reference: str | None = None
    source_url: str | None = None
    confidence: IntelligenceConfidence | None = None
    notes: str | None = None


class DealHeatmapIntentionRead(BaseModel):
    """优纳特有效采购意向只返回推进所需的安全摘要和预计金额。"""

    id: UUID
    customer_name: str
    title: str
    stage: OpportunityStage
    estimated_amount: Decimal = Field(ge=0)
    next_action_at: date | None


class DealHeatmapProvinceDetailRead(BaseModel):
    """点击省份后返回当前卖方成交明细，并独立附加优纳特采购意向。"""

    seller: DealHeatmapSellerRead
    province: str
    signed_amount: Decimal = Field(ge=0)
    signed_order_count: int = Field(ge=0)
    orders: list[DealHeatmapOrderRead]
    intention_amount: Decimal = Field(ge=0)
    intention_count: int = Field(ge=0)
    intentions: list[DealHeatmapIntentionRead]
