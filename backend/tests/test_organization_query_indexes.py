"""单位查询索引离线合同测试：防止面向大批量数据的关键索引被误删。"""

from app.models import Opportunity, Organization, OrganizationContact, OrganizationEvidence, OrganizationSite, SalesProject


def test_organization_query_indexes_cover_pagination_and_relation_loads() -> None:
    """锁定分页复合索引与五类高频一对多外键索引。"""

    expected_indexes = {
        Organization: "ix_organization_updated_at_id",
        OrganizationSite: "ix_organization_site_organization_id",
        OrganizationEvidence: "ix_organization_evidence_organization_id",
        OrganizationContact: "ix_organization_contact_organization_id",
        Opportunity: "ix_opportunity_organization_id",
        SalesProject: "ix_sales_project_organization_id",
    }
    for model, expected_name in expected_indexes.items():
        assert expected_name in {index.name for index in model.__table__.indexes}


def test_sales_project_date_index_supports_insights_period_ranges() -> None:
    """锁定数据洞察全年、季度和月度范围查询使用的签约日期索引。"""

    assert "ix_sales_project_signed_at" in {index.name for index in SalesProject.__table__.indexes}
