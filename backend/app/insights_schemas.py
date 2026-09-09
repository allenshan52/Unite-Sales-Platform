"""数据洞察 API 合同：约束年度区域聚合、趋势、经营提示和导出筛选。"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class InsightsPeriod(str, Enum):
    """支持全年和四个自然季度，作为查询与导出的统一期间枚举。"""

    year = "year"
    q1 = "q1"
    q2 = "q2"
    q3 = "q3"
    q4 = "q4"


class InsightsMetric(str, Enum):
    """限定地图与贡献榜可切换的三个稳定业务指标。"""

    sales = "sales"
    projects = "projects"
    pipeline = "pipeline"


class InsightsScopeMode(str, Enum):
    """负责范围显示精确授权数据，大区视角把任一命中省市扩展到完整销售大区。"""

    assigned = "assigned"
    region = "region"


class InsightsScopeRead(BaseModel):
    """说明响应当前统计到全国、省或市的哪一层。"""

    level: Literal["national", "province", "city"]
    name: str
    province: str | None = None
    city: str | None = None
    mode: InsightsScopeMode = InsightsScopeMode.assigned
    visible_provinces: list[str] = Field(default_factory=list)
    visible_regions: list[str] = Field(default_factory=list)


class InsightsKpisRead(BaseModel):
    """页面核心指标保持金额与数量独立，并附同比/环比。"""

    sales_amount: Decimal
    sales_yoy_percent: Decimal | None
    sales_qoq_percent: Decimal | None
    project_count: int
    projects_yoy_percent: Decimal | None
    projects_qoq_percent: Decimal | None
    average_deal_amount: Decimal
    pipeline_amount: Decimal
    pipeline_count: int
    active_region_count: int


class InsightsRegionRead(BaseModel):
    """省市贡献项同时服务地图着色、排名进度条和城市 Pin。"""

    id: str
    name: str
    province: str
    city: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    sales_amount: Decimal
    project_count: int
    pipeline_amount: Decimal
    pipeline_count: int
    average_deal_amount: Decimal
    metric_value: Decimal
    contribution_percent: Decimal
    rank: int
    yoy_percent: Decimal | None
    qoq_percent: Decimal | None


class InsightsMacroRegionRead(BaseModel):
    """大区金额热力使用七个固定销售大区及其完整省份集合。"""

    id: str
    name: str
    provinces: list[str]
    sales_amount: Decimal
    project_count: int
    pipeline_amount: Decimal
    pipeline_count: int
    metric_value: Decimal
    contribution_percent: Decimal


class InsightsTrendPointRead(BaseModel):
    """月度趋势始终返回十二个月，缺失月份显式补零。"""

    month: int = Field(ge=1, le=12)
    current_amount: Decimal
    previous_amount: Decimal


class InsightsCustomerRead(BaseModel):
    """成交单位榜按当前期间和区域汇总真实项目。"""

    rank: int
    name: str
    province: str
    city: str
    sales_amount: Decimal
    project_count: int
    latest_signed_at: date | None


class InsightsStageRead(BaseModel):
    """当前有效商机按推进阶段展示数量、金额与金额占比。"""

    stage: str
    opportunity_count: int
    amount: Decimal
    percent: Decimal


class InsightsSignalRead(BaseModel):
    """经营提示只由当前聚合结果生成，不保存或硬编码业务结论。"""

    tone: Literal["positive", "warning", "neutral"]
    title: str
    description: str


class InsightsOverviewRead(BaseModel):
    """数据洞察单页聚合响应，避免浏览器并发拼装多个口径。"""

    year: int
    period: InsightsPeriod
    metric: InsightsMetric
    available_years: list[int]
    scope: InsightsScopeRead
    aggregated_at: datetime
    kpis: InsightsKpisRead
    regions: list[InsightsRegionRead]
    macro_regions: list[InsightsMacroRegionRead] = Field(default_factory=list)
    trend: list[InsightsTrendPointRead]
    signals: list[InsightsSignalRead]
    top_customers: list[InsightsCustomerRead]
    stages: list[InsightsStageRead]
