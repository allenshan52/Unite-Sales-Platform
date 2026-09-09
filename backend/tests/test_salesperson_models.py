"""销售人员数据库模型测试：离线校验覆盖、活动、业绩归属和货币精度。"""

from sqlalchemy import CheckConstraint, Numeric, UniqueConstraint

from app.models import (
    Opportunity,
    SalesActivity,
    SalesActivityType,
    Salesperson,
    SalespersonCoverageScope,
    SalesProject,
)


def test_salesperson_domain_uses_explicit_tables_and_activity_types() -> None:
    """销售主档、城市覆盖和活动流水保持独立表，活动口径固定为需求中的三类。"""

    assert Salesperson.__tablename__ == "salesperson"
    assert SalespersonCoverageScope.__tablename__ == "salesperson_coverage_city"
    assert SalesActivity.__tablename__ == "sales_activity"
    assert [item.value for item in SalesActivityType] == ["拜访", "演示", "市场活动"]


def test_coverage_allows_shared_scopes_but_rejects_person_duplicates() -> None:
    """唯一约束只限制同一销售重复范围，不阻止多名销售覆盖同一区域。"""

    unique_constraints = [
        constraint
        for constraint in SalespersonCoverageScope.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    ]
    coverage_constraint = next(constraint for constraint in unique_constraints if constraint.name == "uq_salesperson_coverage_scope")
    assert [column.name for column in coverage_constraint.columns] == ["salesperson_id", "scope_level", "scope_name"]


def test_salesperson_constraints_and_indexes_match_map_queries() -> None:
    """颜色、行政区编码和时间范围查询均由数据库约束或复合索引保护。"""

    constraint_names = {
        constraint.name
        for model in (Salesperson, SalespersonCoverageScope, SalesActivity)
        for constraint in model.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert {
        "ck_salesperson_color_hex",
        "ck_salesperson_coverage_center_gcj02_bounds",
        "ck_salesperson_coverage_city_adcode",
        "ck_salesperson_coverage_scope_fields",
        "ck_sales_activity_adcode",
    } <= constraint_names
    index_names = {
        index.name
        for model in (SalespersonCoverageScope, SalesActivity, Opportunity, SalesProject)
        for index in model.__table__.indexes
    }
    assert {
        "ix_salesperson_coverage_city_adcode",
        "ix_salesperson_coverage_scope_level_name",
        "ix_sales_activity_salesperson_occurred_at",
        "ix_sales_activity_adcode_occurred_at",
        "ix_opportunity_salesperson_stage",
        "ix_sales_project_salesperson_signed_at",
    } <= index_names


def test_salesperson_pin_uses_required_coordinates() -> None:
    """每位销售必须具有可直接绘制 Pin 的中心坐标，且不再保存覆盖半径。"""

    for column_name in ("coverage_center_longitude", "coverage_center_latitude"):
        assert Salesperson.__table__.columns[column_name].nullable is False
    assert "coverage_radius_km" not in Salesperson.__table__.columns


def test_opportunities_and_projects_keep_explicit_salesperson_attribution() -> None:
    """储备与成交分别关联销售人员，人员停用或移除时历史业务记录不会级联删除。"""

    for model in (Opportunity, SalesProject):
        column = model.__table__.columns["salesperson_id"]
        foreign_key = next(iter(column.foreign_keys))
        assert foreign_key.ondelete == "SET NULL"
    activity_foreign_key = next(iter(SalesActivity.__table__.columns["salesperson_id"].foreign_keys))
    assert activity_foreign_key.ondelete == "RESTRICT"


def test_sales_money_fields_remain_fixed_precision() -> None:
    """储备和实际成交使用定点金额，并由数据库拒绝负数污染汇总。"""

    for model, column_name in ((Opportunity, "estimated_amount"), (SalesProject, "contract_amount")):
        column_type = model.__table__.columns[column_name].type
        assert isinstance(column_type, Numeric)
        assert (column_type.precision, column_type.scale) == (14, 2)
    constraint_names = {
        constraint.name
        for model in (Opportunity, SalesProject)
        for constraint in model.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert {
        "ck_opportunity_estimated_amount_nonnegative",
        "ck_sales_project_contract_amount_nonnegative",
    } <= constraint_names
