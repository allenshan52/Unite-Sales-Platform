"""账号数据范围服务测试：覆盖市、省、大区、跨省并集与同行整家公司准入条件。"""

from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.models import Competitor, CompetitorCustomer, CompetitorDeal, CompetitorSite
from app.models import UserRole
from app.sales_coverage import SalesCoverageLevel
from fastapi import HTTPException

from app.services.account_access import (
    account_data_scope,
    competitor_order_location_condition,
    competitor_visibility_condition,
    coverage_scope_is_visible,
    location_is_visible,
    require_location_access,
    unite_deal_visibility_condition,
)
from app.services.organizations import list_organizations


def _user(*scopes):
    """用最小账号形状构造覆盖范围，不依赖数据库会话。"""

    return SimpleNamespace(username="scope_test", role=UserRole.employee, coverage_scopes=list(scopes))


def _scope(level: SalesCoverageLevel, name: str, province: str | None = None, city: str | None = None):
    """构造一个与 ORM coverage scope 属性一致的测试对象。"""

    return SimpleNamespace(scope_level=level, scope_name=name, province=province, city=city)


def test_account_scope_unions_provinces_and_preserves_exact_city() -> None:
    """跨省权限按并集合并，市级权限在负责范围模式下不扩大到整省。"""

    data_scope = account_data_scope(_user(
        _scope(SalesCoverageLevel.province, "吉林", "吉林"),
        _scope(SalesCoverageLevel.province, "辽宁", "辽宁"),
        _scope(SalesCoverageLevel.city, "杭州市", "浙江", "杭州市"),
    ))

    assert data_scope.provinces == frozenset({"吉林", "辽宁"})
    assert data_scope.cities == frozenset({("浙江", "杭州市")})
    assert data_scope.visible_provinces == frozenset({"吉林", "辽宁", "浙江"})


def test_region_mode_expands_any_covered_city_to_full_macro_region() -> None:
    """只负责杭州市的账号切换大区视角后可见完整浙江区。"""

    data_scope = account_data_scope(
        _user(_scope(SalesCoverageLevel.city, "杭州市", "浙江", "杭州市")),
        expand_regions=True,
    )

    assert data_scope.regions == frozenset({"浙江区"})
    assert data_scope.provinces == frozenset({"浙江", "江西"})
    assert not data_scope.cities


def test_location_visibility_keeps_city_scope_exact() -> None:
    """杭州市权限只能命中杭州市，不能因省份相同而看到宁波。"""

    data_scope = account_data_scope(_user(_scope(SalesCoverageLevel.city, "杭州市", "浙江", "杭州市")))

    assert location_is_visible(data_scope, "浙江省", "杭州市") is True
    assert location_is_visible(data_scope, "浙江省", "宁波市") is False
    assert location_is_visible(data_scope, "江苏省", "南京市") is False


def test_region_write_scope_intersects_owned_province_but_rejects_national() -> None:
    """负责吉林的账号可维护北区跨省销售档案，但不能借交集升级为全国权限。"""

    data_scope = account_data_scope(_user(_scope(SalesCoverageLevel.province, "吉林", "吉林")))

    assert coverage_scope_is_visible(data_scope, SalesCoverageLevel.region, "北区", None, None) is True
    assert coverage_scope_is_visible(data_scope, SalesCoverageLevel.region, "南区", None, None) is False
    assert coverage_scope_is_visible(data_scope, SalesCoverageLevel.national, "全国", None, None) is False


def test_out_of_scope_write_returns_forbidden() -> None:
    """市级账号写入其他城市时必须在服务层返回明确 403。"""

    data_scope = account_data_scope(_user(_scope(SalesCoverageLevel.city, "杭州市", "浙江", "杭州市")))

    with pytest.raises(HTTPException) as error:
        require_location_access(data_scope, "浙江省", "宁波市")
    assert error.value.status_code == 403


def test_admin_organization_list_applies_account_scope_to_count_and_rows() -> None:
    """数据后台单位主列表的总数和记录查询都必须包含账号负责省份，不能退化为全国数据。"""

    class ScalarRows:
        """为列表查询返回最小空结果，同时保留传入的 SQL 供断言。"""

        def all(self) -> list[object]:
            return []

    class RecordingDb:
        """记录单位列表发出的计数和记录 SQL，不连接真实数据库。"""

        def __init__(self) -> None:
            self.statements: list[object] = []

        def scalar(self, statement: object) -> int:
            self.statements.append(statement)
            return 0

        def scalars(self, statement: object) -> ScalarRows:
            self.statements.append(statement)
            return ScalarRows()

    db = RecordingDb()
    data_scope = account_data_scope(_user(_scope(SalesCoverageLevel.province, "吉林", "吉林")))

    list_organizations(
        db,  # type: ignore[arg-type]
        page=1,
        page_size=10,
        search=None,
        types=[],
        customer_statuses=[],
        review_statuses=[],
        province=None,
        city=None,
        district=None,
        geocode_status=None,
        sports_only=False,
        data_scope=data_scope,
    )

    assert len(db.statements) == 2
    for statement in db.statements:
        sql = str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        assert "organization_site" in sql
        assert "吉林" in sql


def test_competitor_visibility_requires_site_or_deal_customer_in_scope() -> None:
    """同行准入 SQL 同时检查据点和带成交订单的客户，准入后由上层返回整家公司。"""

    data_scope = account_data_scope(_user(_scope(SalesCoverageLevel.province, "吉林", "吉林")))
    sql = str(
        competitor_visibility_condition(data_scope).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert Competitor.__tablename__ in sql
    assert CompetitorSite.__tablename__ in sql
    assert CompetitorDeal.__tablename__ in sql
    assert CompetitorCustomer.__tablename__ in sql
    assert "吉林" in sql


def test_order_scope_uses_complete_snapshot_and_only_falls_back_when_missing() -> None:
    """订单已有完整省市时不得因关联单位在负责范围内而越权；仅双空历史记录允许回退。"""

    data_scope = account_data_scope(_user(_scope(SalesCoverageLevel.province, "吉林", "吉林")))
    unite_sql = str(unite_deal_visibility_condition(data_scope).compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True},
    ))
    competitor_sql = str(competitor_order_location_condition(data_scope).compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True},
    ))

    for sql in (unite_sql, competitor_sql):
        assert "province IS NOT NULL" in sql
        assert "city IS NOT NULL" in sql
        assert "province IS NULL" in sql
        assert "city IS NULL" in sql
        assert "吉林" in sql
