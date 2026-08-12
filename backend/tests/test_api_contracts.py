"""API 合同测试：覆盖公开目录、管理员保护及单位证据输入约束。"""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.database import get_db
from app.main import app
from app.routers.organizations import filter_options
from app.models import OrganizationContact
from app.schemas import ContactUpdate, OrganizationAdminCreate, OrganizationCreate
from app.services.auth import get_current_admin
from app.services.organizations import _ensure_organization_is_not_duplicate, _sync_related_records, create_organization


def valid_university_payload() -> dict[str, object]:
    """提供不含真实客户信息的最小高校录入样例，专用于输入校验测试。"""

    return {
        "name": "示例生物检测学院（演示）",
        "organization_type": "高校",
        "evidences": [{"evidence_kind": "院系/专业目录", "title": "演示专业目录", "source_url": "https://example.test/major"}],
    }


def organization_response_payload() -> dict[str, object]:
    """提供管理员编辑接口所需的完整虚构响应，避免测试依赖真实数据库。"""

    timestamp = datetime(2026, 8, 10, tzinfo=UTC).isoformat()
    return {
        "id": str(UUID(int=1)),
        "name": "示例检测学院（演示）",
        "organization_type": "高校",
        "industry": "高校科研与检测",
        "customer_status": "潜在客户",
        "review_status": "待核验",
        "inclusion_reason": "公开目录收录",
        "is_sports_exception": False,
        "parent_group": None,
        "website": "https://example.test",
        "unified_social_credit_code": None,
        "recent_follow_up_at": timestamp,
        "recent_follow_up_content": "演示跟进内容",
        "follow_up_owner": "演示负责人",
        "cooperation_intent": "计划开展检测合作",
        "cooperation_level": "二级",
        "notes": None,
        "sites": [{
            "id": str(UUID(int=2)),
            "site_name": "主校区",
            "raw_address": "演示原始地址",
            "address": "演示标准地址",
            "province": "河南省",
            "city": "郑州市",
            "district": "金水区",
            "amap_adcode": "410105",
            "geocode_status": "已定位",
            "geocode_confidence": 95,
            "longitude": 113.6,
            "latitude": 34.8,
            "is_primary": True,
        }],
        "evidences": [],
        "contacts": [{
            "id": str(UUID(int=3)), "name": "演示联系人", "department": "实验中心", "title": "主任",
            "mobile": None, "email": "contact@example.test", "is_primary": True, "is_active": True, "notes": None,
        }],
        "opportunities": [{
            "id": str(UUID(int=4)), "title": "演示检测商机", "stage": "方案/报价", "estimated_amount": "120000.00",
            "ai_summary": None, "next_action": "发送演示方案", "next_action_at": "2026-08-18",
        }],
        "sales_projects": [{
            "id": str(UUID(int=5)), "opportunity_id": str(UUID(int=4)), "name": "演示成交项目",
            "contract_amount": "88000.00", "signed_at": "2026-08-08", "project_detail": "演示项目详情",
        }],
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def sales_office_response_payload() -> dict[str, object]:
    """提供不含真实办公地址的销售常驻点响应，供公开与管理员 API 合同测试复用。"""

    timestamp = datetime(2026, 8, 10, tzinfo=UTC).isoformat()
    return {
        "id": str(UUID(int=101)), "name": "杭州销售常驻点（演示）", "city": "杭州市",
        "address": "杭州市（演示中心点）", "longitude": 120.1551, "latitude": 30.2741,
        "coverage_radius_km": 420, "is_active": True, "created_at": timestamp, "updated_at": timestamp,
    }


def public_channel_partner_payload() -> dict[str, object]:
    """提供公开地图所需的最小渠道演示点，并排除合同和内部备注。"""

    return {
        "id": str(UUID(int=201)), "name": "经销商1", "partner_type": "经销商",
        "address": "济南市市中心（演示）", "map_longitude": 117.1201, "map_latitude": 36.6512,
        "coverage_radius_km": 380, "cooperation_level": "一级",
    }


def channel_partner_response_payload() -> dict[str, object]:
    """提供管理端完整渠道演示档案，验证可空业务字段和更新响应。"""

    timestamp = datetime(2026, 8, 10, tzinfo=UTC).isoformat()
    return {
        "id": str(UUID(int=201)), "name": "经销商1", "partner_type": "经销商",
        "address": "济南市市中心（演示）", "longitude": None, "latitude": None,
        "display_longitude": 117.1201, "display_latitude": 36.6512,
        "authorized_coverage_area": None, "coverage_radius_km": 380,
        "authorized_product_lines": None, "cooperation_level": "一级",
        "contract_info": None, "notes": None, "is_active": True,
        "created_at": timestamp, "updated_at": timestamp,
    }


def test_health_check_succeeds_without_authentication() -> None:
    """健康检查不能依赖管理员会话或业务数据库记录。"""

    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_organization_list_requires_admin_session() -> None:
    """单位名单在未认证访问时必须被拦截，避免真实数据意外暴露。"""

    with TestClient(app) as client:
        response = client.get("/api/v1/organizations")
    assert response.status_code == 401
    assert response.json()["detail"] == "请先登录管理后台"


def test_organization_create_requires_admin_session() -> None:
    """新增单位 API 必须拒绝未认证请求。"""

    with TestClient(app) as client:
        response = client.post("/api/v1/organizations", json={
            "name": "示例疾控中心（演示）",
            "organization_type": "疾控",
            "primary_site": {"province": "河南省", "city": "郑州市"},
        })
    assert response.status_code == 401


def test_organization_create_requires_province_and_city() -> None:
    """管理员新增单位至少要填写省、市，避免产生无法归属地图区域的记录。"""

    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/organizations", json={
                "name": "示例疾控中心（演示）",
                "organization_type": "疾控",
                "primary_site": {"province": "河南省"},
            })
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
    assert "新增单位必须填写省份和城市" in response.text


def test_admin_can_create_organization_with_business_records(monkeypatch: pytest.MonkeyPatch) -> None:
    """新增接口把主地点、联系人、成交项目、商机与证据一次交给服务层。"""

    response_payload = organization_response_payload()

    def fake_create(_db: object, payload: OrganizationAdminCreate, username: str) -> dict[str, object]:
        assert username == "admin_test"
        assert payload.primary_site.city == "郑州市"
        assert payload.contacts[0].name == "演示联系人"
        assert payload.sales_projects[0].contract_amount == 88000
        assert payload.opportunities[0].stage.value == "方案/报价"
        assert payload.evidences[0].evidence_kind.value == "官方名录"
        return response_payload

    monkeypatch.setattr("app.routers.organizations.create_organization", fake_create)
    monkeypatch.setattr("app.routers.organizations.to_read", lambda value: value)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/organizations", json={
                "name": "示例检测学院（演示）",
                "organization_type": "高校",
                "primary_site": {"province": "河南省", "city": "郑州市", "district": "金水区"},
                "contacts": [{"name": "演示联系人", "is_primary": True}],
                "sales_projects": [{"name": "演示成交项目", "contract_amount": 88000}],
                "opportunities": [{"title": "演示检测商机", "stage": "方案/报价"}],
                "evidences": [{"evidence_kind": "官方名录", "title": "演示官方名录", "source_url": "https://example.test/list"}],
            })
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 201
    assert response.json()["name"] == "示例检测学院（演示）"


def test_create_service_warns_about_duplicate_name() -> None:
    """标准化同名单位返回 409，管理员可回到表单核对而非静默重复写入。"""

    class DuplicateDb:
        def scalar(self, _statement: object) -> SimpleNamespace:
            return SimpleNamespace(name="示例检测学院")

    with pytest.raises(HTTPException) as error:
        _ensure_organization_is_not_duplicate(DuplicateDb(), "示例 检测学院")  # type: ignore[arg-type]
    assert error.value.status_code == 409
    assert "已存在同名单位" in error.value.detail


def test_create_service_rolls_back_all_related_records_on_failure() -> None:
    """新增事务中任一写入失败时必须回滚，不能留下半套单位关联数据。"""

    class FailingCreateDb:
        def __init__(self) -> None:
            self.committed = False
            self.rolled_back = False

        def scalar(self, _statement: object) -> None:
            return None

        def add(self, _record: object) -> None:
            return None

        def flush(self) -> None:
            raise RuntimeError("模拟关联写入失败")

        def commit(self) -> None:
            self.committed = True

        def rollback(self) -> None:
            self.rolled_back = True

    db = FailingCreateDb()
    payload = OrganizationAdminCreate.model_validate({
        "name": "示例疾控中心（演示）",
        "organization_type": "疾控",
        "primary_site": {"province": "河南省", "city": "郑州市"},
        "contacts": [{"name": "演示联系人"}],
        "opportunities": [{"title": "演示商机"}],
        "sales_projects": [{"name": "演示成交项目", "contract_amount": 1000}],
    })
    with pytest.raises(RuntimeError, match="模拟关联写入失败"):
        create_organization(db, payload, "admin_test")  # type: ignore[arg-type]
    assert db.rolled_back is True
    assert db.committed is False


def test_filter_options_requires_admin_session() -> None:
    """筛选枚举同样受管理员会话保护，避免组织所在地信息被匿名枚举。"""

    with TestClient(app) as client:
        response = client.get("/api/v1/organizations/filters")
    assert response.status_code == 401
    assert response.json()["detail"] == "请先登录管理后台"


def test_organization_delete_requires_admin_session() -> None:
    """永久删除入口必须与列表相同地受管理员会话保护。"""

    with TestClient(app) as client:
        response = client.delete(f"/api/v1/organizations/{UUID(int=1)}")
    assert response.status_code == 401


def test_admin_can_delete_organization(monkeypatch: pytest.MonkeyPatch) -> None:
    """通过认证的删除请求返回 204，并把单位与操作者交给服务层。"""

    captured: dict[str, object] = {}

    def fake_delete(_db: object, organization_id: UUID, username: str) -> None:
        captured.update(organization_id=organization_id, username=username)

    monkeypatch.setattr("app.routers.organizations.delete_organization", fake_delete)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.delete(f"/api/v1/organizations/{UUID(int=1)}")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 204
    assert captured == {"organization_id": UUID(int=1), "username": "admin_test"}


def test_admin_can_update_primary_site(monkeypatch: pytest.MonkeyPatch) -> None:
    """编辑接口接受单位主档与主地点组合，并返回刷新后的完整档案。"""

    response_payload = organization_response_payload()

    def fake_update(_db: object, _organization_id: UUID, payload: object, _username: str) -> dict[str, object]:
        assert payload.primary_site.province == "河南省"
        assert payload.contacts[0].name == "演示联系人"
        assert payload.sales_projects[0].contract_amount == 88000
        assert payload.opportunities[0].stage.value == "方案/报价"
        return response_payload

    monkeypatch.setattr("app.routers.organizations.update_organization", fake_update)
    monkeypatch.setattr("app.routers.organizations.to_read", lambda value: value)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/organizations/{UUID(int=1)}",
                json={
                    "name": "示例检测学院（演示）",
                    "recent_follow_up_content": "演示跟进内容",
                    "contacts": [{"name": "演示联系人", "is_primary": True}],
                    "sales_projects": [{"name": "演示成交项目", "contract_amount": 88000}],
                    "opportunities": [{"title": "演示检测商机", "stage": "方案/报价"}],
                    "primary_site": {"province": "河南省", "geocode_status": "已定位", "longitude": 113.6, "latitude": 34.8},
                },
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["sites"][0]["province"] == "河南省"


def test_organization_update_rejects_negative_contract_amount() -> None:
    """成交金额必须保持非负，非法金额在进入事务前返回 422。"""

    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/organizations/{UUID(int=1)}",
                json={"sales_projects": [{"name": "演示成交项目", "contract_amount": -1}]},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


def test_related_contact_records_are_updated_added_and_removed_together() -> None:
    """单位保存时按当前表单集合更新、新增和移除联系人，避免残留已删除的旧记录。"""

    kept = OrganizationContact(id=UUID(int=31), name="旧联系人", is_primary=False, is_active=True)
    removed = OrganizationContact(id=UUID(int=32), name="待移除联系人", is_primary=False, is_active=True)

    class SyncDb:
        """记录服务层请求删除的 ORM 对象，不依赖真实数据库。"""

        def __init__(self) -> None:
            self.deleted: list[OrganizationContact] = []

        def delete(self, record: OrganizationContact) -> None:
            """保存待删除对象，供集合同步断言使用。"""

            self.deleted.append(record)

    db = SyncDb()
    records = [kept, removed]
    _sync_related_records(
        db,  # type: ignore[arg-type]
        records,
        [
            ContactUpdate(id=kept.id, name="更新后的联系人", department="实验中心", is_primary=True),
            ContactUpdate(name="新增联系人", title="主任"),
        ],
        OrganizationContact,
        "联系人",
    )

    assert kept.name == "更新后的联系人"
    assert kept.department == "实验中心"
    assert kept.is_primary is True
    assert records[-1].name == "新增联系人"
    assert db.deleted == [removed]


def test_related_contact_record_must_belong_to_current_organization() -> None:
    """拒绝通过其他单位的子记录 ID 越权修改联系人。"""

    class SyncDb:
        """异常路径无需真实数据库行为。"""

        def delete(self, _record: OrganizationContact) -> None:
            """提供同步服务需要的最小接口。"""

    with pytest.raises(HTTPException) as exc_info:
        _sync_related_records(
            SyncDb(),  # type: ignore[arg-type]
            [],
            [ContactUpdate(id=UUID(int=99), name="越权联系人")],
            OrganizationContact,
            "联系人",
        )

    assert exc_info.value.status_code == 422


def test_organization_update_rejects_invalid_longitude() -> None:
    """地点坐标在进入更新服务前按中国范围校验，防止无效 pin 写入数据库。"""

    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.patch(f"/api/v1/organizations/{UUID(int=1)}", json={"primary_site": {"longitude": 150, "latitude": 34.8}})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


def test_public_filter_options_allow_anonymous_access() -> None:
    """公开主站无需管理员 Cookie 也能读取完整地点层级筛选项。"""

    class ScalarRows:
        def __init__(self, values: list[str]) -> None:
            self.values = values

        def all(self) -> list[str]:
            return self.values

    class FilterOptionsDb:
        def __init__(self) -> None:
            self.responses = iter([["河南省"], ["安阳市"], ["文峰区"]])

        def scalars(self, _statement: object) -> ScalarRows:
            return ScalarRows(next(self.responses))

    app.dependency_overrides[get_db] = lambda: FilterOptionsDb()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/organizations/filters", params={"province": "河南省", "city": "安阳市"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["cities"] == ["安阳市"]
    assert response.json()["districts"] == ["文峰区"]


def test_public_province_summaries_allow_anonymous_access(monkeypatch: pytest.MonkeyPatch) -> None:
    """公开热力聚合无需管理员 Cookie，并且只返回省级统计字段。"""

    monkeypatch.setattr(
        "app.routers.organizations.summarize_organizations_by_province",
        lambda _db: [{
            "province": "河南省",
            "total": 39,
            "organization_types": {"高校": 35, "研究院": 4},
            "customer_statuses": {"潜在客户": 30, "商机客户": 7, "已成交客户": 2},
        }],
    )
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/organizations/province-summaries")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == [{
        "province": "河南省",
        "total": 39,
        "organization_types": {"高校": 35, "研究院": 4},
        "customer_statuses": {"潜在客户": 30, "商机客户": 7, "已成交客户": 2},
    }]


def test_public_sales_office_locations_allow_anonymous_access(monkeypatch: pytest.MonkeyPatch) -> None:
    """公开主站无需管理员 Cookie 即可读取启用常驻点的可视化字段。"""

    monkeypatch.setattr("app.routers.sales_office_locations.list_public_sales_office_locations", lambda _db: [sales_office_response_payload()])
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/sales-office-locations")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()[0]["coverage_radius_km"] == 420


def test_sales_office_update_requires_admin_session() -> None:
    """常驻点地址和覆盖半径不能被匿名请求修改。"""

    with TestClient(app) as client:
        response = client.patch(f"/api/v1/sales-office-locations/{UUID(int=101)}", json={"coverage_radius_km": 500})
    assert response.status_code == 401


def test_admin_can_update_sales_office_location(monkeypatch: pytest.MonkeyPatch) -> None:
    """管理员可修改常驻点地址和半径，并获得更新后的完整记录。"""

    captured: dict[str, object] = {}

    def fake_update(_db: object, location_id: UUID, payload: object, username: str) -> dict[str, object]:
        captured.update(location_id=location_id, radius=payload.coverage_radius_km, username=username)
        return {**sales_office_response_payload(), "coverage_radius_km": payload.coverage_radius_km}

    monkeypatch.setattr("app.routers.sales_office_locations.update_sales_office_location", fake_update)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.patch(f"/api/v1/sales-office-locations/{UUID(int=101)}", json={"coverage_radius_km": 500})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["coverage_radius_km"] == 500
    assert captured == {"location_id": UUID(int=101), "radius": 500, "username": "admin_test"}


def test_sales_office_update_rejects_invalid_radius() -> None:
    """不合理的覆盖半径在进入数据库服务前返回输入校验错误。"""

    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.patch(f"/api/v1/sales-office-locations/{UUID(int=101)}", json={"coverage_radius_km": 0})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


def test_public_channel_partner_locations_are_safe_and_anonymous(monkeypatch: pytest.MonkeyPatch) -> None:
    """公开渠道接口无需登录，且响应不包含合同、备注和空业务坐标。"""

    monkeypatch.setattr("app.routers.channel_partner_locations.list_public_channel_partner_points", lambda _db: [public_channel_partner_payload()])
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/channel-partner-locations")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    item = response.json()[0]
    assert item["partner_type"] == "经销商"
    assert "contract_info" not in item and "notes" not in item and "longitude" not in item


def test_channel_partner_update_requires_admin_session() -> None:
    """渠道等级、合同及覆盖字段不能被匿名请求修改。"""

    with TestClient(app) as client:
        response = client.patch(f"/api/v1/channel-partner-locations/{UUID(int=201)}", json={"cooperation_level": "二级"})
    assert response.status_code == 401


def test_admin_can_update_channel_partner_location(monkeypatch: pytest.MonkeyPatch) -> None:
    """管理员可修改渠道等级和覆盖半径，并获得完整更新档案。"""

    captured: dict[str, object] = {}

    def fake_update(_db: object, location_id: UUID, payload: object, username: str) -> dict[str, object]:
        captured.update(location_id=location_id, level=payload.cooperation_level.value, radius=payload.coverage_radius_km, username=username)
        return {**channel_partner_response_payload(), "cooperation_level": payload.cooperation_level.value, "coverage_radius_km": payload.coverage_radius_km}

    monkeypatch.setattr("app.routers.channel_partner_locations.update_channel_partner_location", fake_update)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/channel-partner-locations/{UUID(int=201)}",
                json={"cooperation_level": "二级", "coverage_radius_km": 440},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["cooperation_level"] == "二级"
    assert captured == {"location_id": UUID(int=201), "level": "二级", "radius": 440, "username": "admin_test"}


def test_channel_partner_update_rejects_invalid_radius() -> None:
    """渠道覆盖半径在进入数据库服务前限制为正值。"""

    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.patch(f"/api/v1/channel-partner-locations/{UUID(int=201)}", json={"coverage_radius_km": 0})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


def test_public_organization_list_excludes_admin_only_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """匿名列表仅返回主站字段，详细地址、坐标、备注和证据内容不会泄露。"""

    organization = SimpleNamespace(
        id=UUID(int=1), name="示例高校（演示）", organization_type="高校", industry="高校科研与检测",
        customer_status="潜在客户", review_status="已核验", inclusion_reason="公开目录收录",
        is_sports_exception=False, parent_group=None, website="https://example.test",
        recent_follow_up_at=datetime(2026, 8, 10, tzinfo=UTC), recent_follow_up_content="已完成演示沟通",
        follow_up_owner="内部负责人", cooperation_intent="计划开展检测合作", cooperation_level="二级",
        notes="管理员备注", contacts=[SimpleNamespace(mobile="13800000000")], evidences=[SimpleNamespace(source_url="https://private.example.test")],
        sites=[SimpleNamespace(province="河南省", city="安阳市", district="文峰区", is_primary=True, address="内部详细地址", longitude=114.0, latitude=36.0)],
    )
    monkeypatch.setattr("app.routers.organizations.list_public_organizations", lambda *_args, **_kwargs: ([(organization, 1)], 1))
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/organizations", params={"page": 1, "page_size": 8})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["evidence_count"] == 1
    assert item["recent_follow_up_content"] == "已完成演示沟通"
    assert "notes" not in item and "evidences" not in item and "contacts" not in item and "follow_up_owner" not in item
    assert set(item["sites"][0]) == {"province", "city", "district", "is_primary"}


def test_public_filters_reject_oversized_province() -> None:
    """公开筛选入口沿用地点参数长度校验，异常输入不会进入数据库查询。"""

    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/organizations/filters", params={"province": "省" * 61})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


def test_filter_options_returns_selected_location_hierarchy() -> None:
    """省市筛选返回数据库中的下级城市和区，供地图与单位库保持一致。"""

    class ScalarRows:
        def __init__(self, values: list[str]) -> None:
            self.values = values

        def all(self) -> list[str]:
            return self.values

    class FilterOptionsDb:
        def __init__(self) -> None:
            self.responses = iter([["上海市"], ["上海市"], ["徐汇区", "杨浦区"]])

        def scalars(self, _statement: object) -> ScalarRows:
            return ScalarRows(next(self.responses))

    options = filter_options(province="上海市", city="上海市", db=FilterOptionsDb())
    assert options.provinces == ["上海市"]
    assert options.cities == ["上海市"]
    assert options.districts == ["徐汇区", "杨浦区"]


def test_filter_options_rejects_oversized_province() -> None:
    """地点筛选限制长度，避免异常长查询进入数据库条件。"""

    app.dependency_overrides[get_current_admin] = lambda: object()
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/organizations/filters", params={"province": "省" * 61})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


def test_university_requires_official_evidence() -> None:
    """高校缺少专业/研究方向依据时不能被直接写入候选单位库。"""

    payload = valid_university_payload()
    payload["evidences"] = []
    with pytest.raises(ValidationError, match="必须附至少一条"):
        OrganizationCreate.model_validate(payload)


def test_sports_exception_is_limited_to_universities() -> None:
    """体育例外只用于体育高校，防止被错误用于其他单位类型。"""

    payload = valid_university_payload()
    payload["organization_type"] = "研究院"
    payload["is_sports_exception"] = True
    with pytest.raises(ValidationError, match="仅适用于高校"):
        OrganizationCreate.model_validate(payload)
