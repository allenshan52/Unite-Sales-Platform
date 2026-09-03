"""典型案例 Pydantic 合同：校验匿名展示内容、图片元数据和管理端输入。"""

from datetime import date, datetime
from decimal import Decimal
from pathlib import PurePosixPath
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAINLAND_PROVINCE_ADCODES: dict[str, str] = {
    "北京市": "110000", "天津市": "120000", "河北省": "130000", "山西省": "140000",
    "内蒙古自治区": "150000", "辽宁省": "210000", "吉林省": "220000", "黑龙江省": "230000",
    "上海市": "310000", "江苏省": "320000", "浙江省": "330000", "安徽省": "340000",
    "福建省": "350000", "江西省": "360000", "山东省": "370000", "河南省": "410000",
    "湖北省": "420000", "湖南省": "430000", "广东省": "440000", "广西壮族自治区": "450000",
    "海南省": "460000", "重庆市": "500000", "四川省": "510000", "贵州省": "520000",
    "云南省": "530000", "西藏自治区": "540000", "陕西省": "610000", "甘肃省": "620000",
    "青海省": "630000", "宁夏回族自治区": "640000", "新疆维吾尔自治区": "650000",
}


class TypicalCaseImage(BaseModel):
    """描述仓库内一张案例图片，顺序由 JSON 数组位置决定。"""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    path: str = Field(min_length=12, max_length=500)
    alt_text: str = Field(min_length=2, max_length=240)
    caption: str | None = Field(default=None, max_length=500)
    is_cover: bool = False

    @field_validator("path")
    @classmethod
    def validate_public_path(cls, value: str) -> str:
        """只允许仓库案例目录中的常见 Web 图片，防止路径穿越和任意外链。"""

        path = PurePosixPath(value)
        if not value.startswith("/cases/") or ".." in path.parts:
            raise ValueError("图片路径必须位于 /cases/ 且不能包含上级目录")
        if path.suffix.lower() not in {".webp", ".png", ".jpg", ".jpeg", ".avif"}:
            raise ValueError("图片仅支持 WebP、PNG、JPEG 或 AVIF")
        return value


class TypicalCaseMetric(BaseModel):
    """保存一项经过策展的展示指标，不替代销售项目中的真实金额。"""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    label: str = Field(min_length=1, max_length=40)
    value: str = Field(min_length=1, max_length=40)
    unit: str | None = Field(default=None, max_length=20)
    note: str | None = Field(default=None, max_length=160)


class TypicalCaseInput(BaseModel):
    """一次校验案例主档、展示故事、图片和指标，供原子新增或修改。"""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    sales_project_id: UUID | None = None
    province: str = Field(min_length=2, max_length=60)
    province_adcode: str = Field(pattern=r"^[0-9]{6}$")
    city: str = Field(min_length=2, max_length=60)
    title: str = Field(min_length=2, max_length=160)
    subtitle: str | None = Field(default=None, max_length=240)
    customer_display_name: str = Field(min_length=2, max_length=160)
    industry_label: str = Field(min_length=2, max_length=120)
    summary: str = Field(default="", max_length=2000)
    challenge: str = Field(default="", max_length=10000)
    solution: str = Field(default="", max_length=10000)
    outcome: str = Field(default="", max_length=10000)
    product_scope: str = Field(default="", max_length=5000)
    customer_quote: str | None = Field(default=None, max_length=2000)
    quote_attribution: str | None = Field(default=None, max_length=160)
    show_contract_amount: bool = False
    is_published: bool = False
    is_featured: bool = False
    images: list[TypicalCaseImage] = Field(default_factory=list, max_length=5)
    metrics: list[TypicalCaseMetric] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def validate_case_publishability(self) -> "TypicalCaseInput":
        """锁定大陆省份、封面和公开内容完整性，避免发布半成品或错误口径。"""

        expected_adcode = MAINLAND_PROVINCE_ADCODES.get(self.province)
        if expected_adcode is None or expected_adcode != self.province_adcode:
            raise ValueError("省份与大陆省级行政区编码不匹配")
        cover_count = sum(image.is_cover for image in self.images)
        if cover_count > 1:
            raise ValueError("案例最多只能设置一张封面图")
        if len({metric.label for metric in self.metrics}) != len(self.metrics):
            raise ValueError("成果指标名称不能重复")
        if self.is_featured and not self.is_published:
            raise ValueError("推荐案例必须同时发布")
        if self.show_contract_amount and self.sales_project_id is None:
            raise ValueError("展示合同金额必须关联成交项目")
        if self.is_published:
            required = (self.summary, self.challenge, self.solution, self.outcome, self.product_scope)
            if any(not value.strip() for value in required):
                raise ValueError("发布案例必须完整填写摘要、挑战、方案、成果和产品服务范围")
            if not self.images or cover_count != 1:
                raise ValueError("发布案例必须提供图片且设置一张封面图")
        return self


class TypicalCaseAdminRead(TypicalCaseInput):
    """管理端读取完整案例及关联成交项目的受保护字段。"""

    id: UUID
    project_name: str | None
    organization_name: str | None
    contract_amount: Decimal | None
    signed_at: date | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TypicalCaseAdminListItem(BaseModel):
    """管理列表只返回省级状态摘要，完整故事必须在打开案例后读取。"""

    id: UUID | None
    province: str
    province_adcode: str
    status: Literal["未配置", "草稿", "已上线"]
    city: str | None
    title: str | None
    customer_display_name: str | None
    industry_label: str | None
    cover_image: TypicalCaseImage | None
    is_featured: bool
    updated_at: datetime | None


class TypicalCaseAdminOverview(BaseModel):
    """固定返回大陆 31 个省级槽位及配置状态统计，不提供无意义分页。"""

    total_regions: int
    configured_count: int
    draft_count: int
    published_count: int
    items: list[TypicalCaseAdminListItem]


class TypicalCaseImageUploadRead(BaseModel):
    """图片上传成功后返回可直接写入案例图片元数据的公开路径。"""

    path: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    size_bytes: int = Field(gt=0)


class TypicalCaseProjectOption(BaseModel):
    """为案例编辑器返回可搜索的成交项目和主地点摘要。"""

    id: UUID
    project_name: str
    organization_name: str
    province: str
    city: str
    contract_amount: Decimal
    signed_at: date | None


class TypicalCasePublicSummary(BaseModel):
    """全国案例地图首屏只需的已发布摘要。"""

    id: UUID
    province: str
    province_adcode: str
    city: str
    title: str
    subtitle: str | None
    customer_display_name: str
    industry_label: str
    summary: str
    cover_image: TypicalCaseImage | None
    is_featured: bool


class TypicalCaseMapRegion(BaseModel):
    """一条大陆省级区域及其已发布案例状态。"""

    province: str
    province_adcode: str
    status: Literal["已上线", "筹备中"]
    case: TypicalCasePublicSummary | None


class TypicalCaseMapResponse(BaseModel):
    """一次返回地图完整区域和后端计算的上线统计。"""

    total_regions: int
    published_count: int
    pending_count: int
    regions: list[TypicalCaseMapRegion]


class TypicalCasePublicDetail(BaseModel):
    """公开案例详情只包含发布批准后的去敏故事与可选真实成交口径。"""

    id: UUID
    province: str
    province_adcode: str
    city: str
    title: str
    subtitle: str | None
    customer_display_name: str
    industry_label: str
    summary: str
    challenge: str
    solution: str
    outcome: str
    product_scope: str
    customer_quote: str | None
    quote_attribution: str | None
    images: list[TypicalCaseImage]
    metrics: list[TypicalCaseMetric]
    project_name: str | None
    signed_at: date | None
    contract_amount: Decimal | None
    published_at: datetime | None
