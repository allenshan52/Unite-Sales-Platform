"""已成交客户地图服务测试：验证筛选条件与实际成交金额汇总。"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from app.services.organizations import list_public_won_customer_map_points


class _FakeResult:
    """模拟 SQLAlchemy 结果对象，保留服务使用的 unique/all 调用链。"""

    def __init__(self, rows: list[tuple[object, object]]) -> None:
        self.rows = rows

    def unique(self) -> "_FakeResult":
        """返回当前结果，模拟关联预加载后的去重行为。"""

        return self

    def all(self) -> list[tuple[object, object]]:
        """返回构造好的单位与主地点记录。"""

        return self.rows


class _FakeDb:
    """捕获生成的查询并返回一条已成交客户记录。"""

    def __init__(self, rows: list[tuple[object, object]]) -> None:
        self.rows = rows
        self.statement = ""

    def execute(self, statement: object) -> _FakeResult:
        """记录查询文本，便于断言服务确实使用数据库筛选条件。"""

        self.statement = str(statement)
        return _FakeResult(self.rows)


def test_won_customer_service_filters_resolved_primary_sites_and_sums_actual_projects() -> None:
    """服务只选已成交、已定位主地点，并仅累计 sales_project 合同金额。"""

    projects = [
        SimpleNamespace(id=UUID(int=11), name="项目一", contract_amount=Decimal("680000.00"), signed_at=date(2025, 3, 18), project_detail="演示一"),
        SimpleNamespace(id=UUID(int=12), name="项目二", contract_amount=Decimal("240000.00"), signed_at=date(2026, 1, 12), project_detail="演示二"),
    ]
    organization = SimpleNamespace(
        id=UUID(int=10), name="公司1", organization_type="企业", industry="华东实验室设备",
        customer_status="已成交客户", review_status="已核验", sales_projects=projects,
    )
    site = SimpleNamespace(
        address="上海市浦东新区演示地址", province="上海市", city="上海市", district="浦东新区",
        longitude=121.4917, latitude=31.2174,
    )
    db = _FakeDb([(organization, site)])

    points = list_public_won_customer_map_points(db)  # type: ignore[arg-type]

    assert points[0].deal_count == 2
    assert points[0].actual_sales_amount == Decimal("920000.00")
    assert [deal.name for deal in points[0].deals] == ["项目二", "项目一"]
    assert "organization.customer_status" in db.statement
    assert "organization_site.is_primary" in db.statement
    assert "organization_site.geocode_status" in db.statement
