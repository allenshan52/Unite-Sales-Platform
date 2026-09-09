"""客户集团数据库模型测试：离线校验树、金额和地图字段的关键约束。"""

from sqlalchemy import CheckConstraint, Numeric

from app.models import CustomerGroup, CustomerGroupUnit


def test_customer_group_tables_are_independent_from_organizations() -> None:
    """集团功能使用独立表，避免把现有目标单位主档变成混合模型。"""

    assert CustomerGroup.__tablename__ == "customer_group"
    assert CustomerGroupUnit.__tablename__ == "customer_group_unit"
    assert "organization_id" not in CustomerGroupUnit.__table__.columns


def test_customer_group_unit_money_uses_fixed_precision() -> None:
    """实际和预计金额均使用 NUMERIC，防止货币统计出现浮点误差。"""

    for column_name in ("actual_sales_amount", "estimated_opportunity_amount"):
        column_type = CustomerGroupUnit.__table__.columns[column_name].type
        assert isinstance(column_type, Numeric)
        assert (column_type.precision, column_type.scale) == (14, 2)


def test_customer_group_unit_database_constraints_cover_tree_and_deals() -> None:
    """模型元数据必须保留总部、成交金额、商机金额和坐标边界约束。"""

    constraint_names = {
        constraint.name
        for constraint in CustomerGroupUnit.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert constraint_names == {
        "ck_customer_group_unit_tree_role",
        "ck_customer_group_unit_deal_amount",
        "ck_customer_group_unit_estimated_amount",
        "ck_customer_group_unit_gcj02_bounds",
    }
    headquarters_index = next(index for index in CustomerGroupUnit.__table__.indexes if index.name == "uq_customer_group_single_headquarters")
    assert headquarters_index.unique is True
    assert str(headquarters_index.dialect_options["postgresql"]["where"]) == "is_headquarters"
