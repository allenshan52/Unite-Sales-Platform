"""管理员数据后台 API 合同测试：覆盖权限、分页、校验和完整 CRUD 路径。"""

from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.admin_data_schemas import AdminDataPage
from app.database import get_db
from app.main import app
from app.models import ChannelPartnerType, UserRole
from app.sales_coverage import SalesCoverageLevel
from app.services.admin_data import RESOURCE_DEFINITIONS, list_admin_data, validate_admin_data
from app.services.auth import get_current_admin


def test_admin_data_requires_admin_session() -> None:
    """通用列表不能绕过管理员会话匿名读取业务数据。"""

    with TestClient(app) as client:
        response = client.get("/api/v1/admin-data/salespeople")
    assert response.status_code == 401
    assert response.json()["detail"] == "请先登录"


def test_regional_user_cannot_use_generic_salesperson_resources() -> None:
    """区域账号不能借通用后台接口读取选项或删除销售人员及其子表。"""

    employee = SimpleNamespace(
        username="jilin_sales",
        role=UserRole.employee,
        coverage_scopes=[SimpleNamespace(scope_level=SalesCoverageLevel.province, scope_name="吉林", province="吉林", city=None)],
    )
    app.dependency_overrides[get_current_admin] = lambda: employee
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            list_response = client.get("/api/v1/admin-data/salespeople")
            options_response = client.get("/api/v1/admin-data/salespeople/options")
            delete_response = client.delete(f"/api/v1/admin-data/salespeople/{uuid4()}")
    finally:
        app.dependency_overrides.clear()
    assert {list_response.status_code, options_response.status_code, delete_response.status_code} == {403}
    assert list_response.json()["detail"] == "当前账号没有销售数据库管理权限"


def test_regular_user_cannot_mutate_resource_without_region_fields() -> None:
    """普通用户可进后台，但销售常驻点缺少省份归属时只能由超级管理员修改。"""

    employee = SimpleNamespace(
        username="jilin_sales",
        role=UserRole.employee,
        coverage_scopes=[SimpleNamespace(scope_level=SalesCoverageLevel.province, scope_name="吉林", province="吉林", city=None)],
    )
    app.dependency_overrides[get_current_admin] = lambda: employee
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/admin-data/sales_office_locations", json={"data": {
                "name": "演示常驻点",
                "city": "长春市",
                "address": None,
                "longitude": 125.3,
                "latitude": 43.8,
                "coverage_radius_km": 300,
                "is_active": True,
            }})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert "仅超级管理员" in response.json()["detail"]


def test_admin_data_rejects_invalid_resource_fields() -> None:
    """资源专属 Pydantic 模式拒绝缺失字段，且不会进入数据库服务。"""

    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/admin-data/salespeople", json={"data": {"display_name": "演示销售"}})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
    assert response.json()["detail"].startswith("字段 employee_code")


def test_competitor_admin_accepts_complete_deal_fields_and_validates_new_values() -> None:
    """同行后台完整接收四项产品字段、数量和供应商，并拒绝非法数量与官网。"""

    customer_id = uuid4()
    values = validate_admin_data("competitor_deals", {
        "competitor_customer_id": customer_id,
        "project_name": "虚构色谱仪采购项目",
        "deal_type": "设备采购",
        "product_name": "台式气相色谱仪",
        "specification_model": "GC-DEMO-01",
        "product_image_url": "/cases/demo.webp",
        "unit_price": "120000.00",
        "quantity": "2.000",
        "supplier_name": "虚构仪器供应商",
        "amount": "240000.00",
        "signed_at": "2026-08-20",
        "source_type": "公开信息",
        "source_reference": "虚构中标公告",
        "source_url": "https://example.com/source",
        "confidence": "高",
        "notes": "纯虚构测试数据",
        "products": [{
            "product_name": "台式气相色谱仪",
            "brand": "虚构仪器品牌",
            "specification_model": "GC-DEMO-01",
            "product_image_url": "/cases/demo.webp",
            "unit_price": "120000.00",
            "quantity": "2.000",
            "line_total": "240000.00",
        }],
    })
    assert values["product_name"] == "台式气相色谱仪"
    assert values["unit_price"] == Decimal("120000.00")
    assert values["quantity"] == Decimal("2.000")
    assert values["supplier_name"] == "虚构仪器供应商"
    assert values["products"][0]["brand"] == "虚构仪器品牌"

    with pytest.raises(HTTPException) as quantity_error:
        validate_admin_data("competitor_deals", {**values, "quantity": 0})
    assert quantity_error.value.status_code == 422

    with pytest.raises(HTTPException) as website_error:
        validate_admin_data("competitors", {
            "name": "虚构同行",
            "website_url": "ftp://example.com",
            "color": "#25846F",
            "description": None,
            "is_active": True,
        })
    assert website_error.value.status_code == 422


def test_admin_data_list_create_update_and_delete(monkeypatch) -> None:
    """认证管理员可分页读取、新增、完整编辑并删除白名单资源。"""

    record_id = uuid4()
    captured: dict[str, object] = {}

    def fake_list(
        _db,
        resource: str,
        *,
        page: int,
        page_size: int,
        search: str | None,
        partner_type: ChannelPartnerType | None,
        parent_id: UUID | None,
        data_scope: object,
        actor_username: str,
    ) -> AdminDataPage:
        """记录分页参数并返回一条可序列化演示数据。"""

        captured["list"] = (resource, page, page_size, search, partner_type, parent_id)
        captured["scope"] = (getattr(data_scope, "unrestricted", False), actor_username)
        return AdminDataPage(items=[{"id": record_id, "display_name": "演示销售"}], total=1, page=page, page_size=page_size)

    def fake_create(_db, resource: str, values: dict, actor: str) -> dict:
        """捕获新增服务输入。"""

        captured["create"] = (resource, values, actor)
        return {"id": record_id, **values}

    def fake_update(_db, resource: str, requested_id: UUID, values: dict, actor: str) -> dict:
        """捕获编辑服务输入。"""

        captured["update"] = (resource, requested_id, values, actor)
        return {"id": requested_id, **values}

    def fake_delete(_db, resource: str, requested_id: UUID, actor: str) -> None:
        """捕获删除服务输入。"""

        captured["delete"] = (resource, requested_id, actor)

    monkeypatch.setattr("app.routers.admin_data.list_admin_data", fake_list)
    monkeypatch.setattr("app.routers.admin_data.create_admin_data", fake_create)
    monkeypatch.setattr("app.routers.admin_data.update_admin_data", fake_update)
    monkeypatch.setattr("app.routers.admin_data.delete_admin_data", fake_delete)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    payload = {
        "employee_code": "DEMO-S009",
        "display_name": "演示销售",
        "color": "#2878B5",
        "coverage_center_longitude": 116.4,
        "coverage_center_latitude": 39.9,
        "is_active": True,
    }
    try:
        with TestClient(app) as client:
            list_response = client.get("/api/v1/admin-data/channel_partners?page=2&page_size=25&search=演示&partner_type=代理商")
            create_response = client.post("/api/v1/admin-data/salespeople", json={"data": payload})
            update_response = client.put(f"/api/v1/admin-data/salespeople/{record_id}", json={"data": payload})
            delete_response = client.delete(f"/api/v1/admin-data/salespeople/{record_id}")
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert captured["list"] == ("channel_partners", 2, 25, "演示", ChannelPartnerType.agent, None)
    assert captured["scope"] == (True, "admin_test")
    assert create_response.status_code == 201
    assert captured["create"][0::2] == ("salespeople", "admin_test")  # type: ignore[index]
    assert update_response.status_code == 200
    assert captured["update"][0] == "salespeople"  # type: ignore[index]
    assert delete_response.status_code == 204
    assert captured["delete"] == ("salespeople", record_id, "admin_test")


def test_admin_data_registry_covers_all_requested_tables() -> None:
    """锁定五个后台页面涉及的十三张非目标单位业务表。"""

    assert set(RESOURCE_DEFINITIONS) == {
        "sales_office_locations", "channel_partners", "customer_groups", "customer_group_units",
        "competitors", "competitor_sites", "competitor_customers", "competitor_deals",
        "competitor_strength_regions", "competitor_links", "salespeople",
        "salesperson_coverage_cities", "sales_activities",
    }


def test_admin_data_list_forwards_parent_scope(monkeypatch) -> None:
    """同行详情的子表列表必须把受控父记录 ID 原样交给服务层。"""

    parent_id = uuid4()
    captured: dict[str, object] = {}

    def fake_list(_db, resource: str, **parameters: object) -> AdminDataPage:
        """捕获详情工作区的父记录筛选参数。"""

        captured.update(parameters)
        return AdminDataPage(items=[], total=0, page=1, page_size=10)

    monkeypatch.setattr("app.routers.admin_data.list_admin_data", fake_list)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/admin-data/competitor_sites?parent_id={parent_id}")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert captured["parent_id"] == parent_id


def test_admin_data_rejects_parent_scope_for_unregistered_resource() -> None:
    """父记录筛选只能用于显式登记的同行子表，不能变成任意字段过滤入口。"""

    with pytest.raises(HTTPException) as error:
        list_admin_data(object(), "competitors", page=1, page_size=10, search=None, parent_id=uuid4())  # type: ignore[arg-type]
    assert error.value.status_code == 400
    assert error.value.detail == "该数据类型不支持父记录筛选"
