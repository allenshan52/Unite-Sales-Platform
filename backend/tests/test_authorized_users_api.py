"""站点账号管理 API 合同：覆盖超级管理员保护、范围校验及账号增改删。"""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, call
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.database import get_db
from app.main import app
from app.models import UserRole
from app.routers import authorized_users as users_router
from app.sales_coverage import SalesCoverageLevel
from app.services.auth import get_current_admin, get_current_super_admin, get_current_user
from app.schemas import AuthorizedUserCoverageScopeInput
from app.services import authorized_users as authorized_user_service


def _scope(scope_id: int, level: SalesCoverageLevel, name: str, *, province: str | None = None) -> SimpleNamespace:
    """生成一条不依赖数据库的虚构账号范围。"""

    return SimpleNamespace(
        id=UUID(int=scope_id),
        scope_level=level,
        scope_name=name,
        province=province,
        city=None,
        amap_adcode=None,
    )


def _user(user_id: int, username: str, role: UserRole, *, is_current: bool = False) -> SimpleNamespace:
    """生成不含密码字段的虚构账号对象供路由合同测试使用。"""

    now = datetime(2026, 8, 25, 9, 0, tzinfo=UTC)
    scopes = [_scope(user_id, SalesCoverageLevel.national, "全国")] if role is UserRole.admin else [
        _scope(user_id, SalesCoverageLevel.province, "吉林", province="吉林")
    ]
    return SimpleNamespace(
        id=UUID(int=user_id),
        username=username,
        role=role,
        salesperson_id=None if role is UserRole.admin else UUID(int=501),
        salesperson=None if role is UserRole.admin else SimpleNamespace(display_name="演示销售", employee_code="DEMO-X001"),
        is_active=True,
        last_login_at=now if is_current else None,
        created_at=now,
        coverage_scopes=scopes,
    )


def _province_payload(name: str = "吉林") -> dict[str, object]:
    """返回一条合法省级账号覆盖输入。"""

    return {"scope_level": "省", "scope_name": name, "province": name, "city": None, "amap_adcode": None}


def test_home_data_requires_authorized_session() -> None:
    """未登录浏览器不能读取任何原公开主站业务接口。"""

    with TestClient(app) as client:
        response = client.get("/api/v1/public/organizations/filters")
    assert response.status_code == 401
    assert response.json()["detail"] == "请先登录"


def test_regular_user_cannot_manage_authorized_users() -> None:
    """普通用户会话可看主站，但不能进入授权账号管理 API。"""

    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_user] = lambda: _user(2, "employee_test", UserRole.employee)
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/authorized-users")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403
    assert response.json()["detail"] == "当前账号没有超级管理员权限"


def test_regular_user_can_enter_data_backend_but_not_user_management() -> None:
    """普通用户通过数据后台会话依赖，超级管理员依赖仍单独拒绝。"""

    employee = _user(2, "employee_test", UserRole.employee)
    assert get_current_admin(employee) is employee
    try:
        get_current_super_admin(employee)
    except Exception as error:
        assert getattr(error, "status_code", None) == 403
    else:
        raise AssertionError("普通用户不应通过授权账号管理依赖")


def test_super_admin_can_list_safe_user_and_scope_fields(monkeypatch) -> None:
    """账号目录返回身份和范围，但绝不暴露密码哈希或锁定内部字段。"""

    admin = _user(1, "admin_syt", UserRole.admin, is_current=True)
    employee = _user(2, "jilin_sales", UserRole.employee)
    monkeypatch.setattr(users_router, "list_authorized_users", lambda _db: [admin, employee])
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_super_admin] = lambda: admin
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/authorized-users")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()[0]["is_current"] is True
    assert response.json()[0]["is_protected"] is True
    assert response.json()[1]["role"] == "普通用户"
    assert response.json()[1]["coverage_scopes"][0]["included_provinces"] == ["吉林"]
    assert "password_hash" not in response.json()[0]


def test_create_validates_password_scope_and_supports_success(monkeypatch) -> None:
    """短密码和空范围在路由层拒绝，合规凭据可创建普通用户。"""

    admin = _user(1, "admin_syt", UserRole.admin, is_current=True)
    created = _user(3, "new.employee", UserRole.employee)
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        users_router,
        "create_authorized_user",
        lambda _db, username, _password, salesperson_id, scopes: captured.update(username=username, salesperson_id=salesperson_id, scopes=scopes) or created,
    )
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_super_admin] = lambda: admin
    valid = {"username": "new.employee", "password": "safe-password-2026", "salesperson_id": str(UUID(int=501)), "coverage_scopes": [_province_payload()]}
    try:
        with TestClient(app) as client:
            short_password = client.post("/api/v1/authorized-users", json={**valid, "password": "short"})
            empty_scope = client.post("/api/v1/authorized-users", json={**valid, "coverage_scopes": []})
            response = client.post("/api/v1/authorized-users", json=valid)
    finally:
        app.dependency_overrides.clear()
    assert short_password.status_code == 422
    assert empty_scope.status_code == 422
    assert response.status_code == 201
    assert response.json()["username"] == "new.employee"
    assert captured["username"] == "new.employee"
    assert captured["salesperson_id"] == UUID(int=501)
    assert len(captured["scopes"]) == 1


def test_scope_collection_rejects_duplicate_and_mixed_national(monkeypatch) -> None:
    """重复范围及全国与其他范围并存都不能进入服务层。"""

    admin = _user(1, "admin_syt", UserRole.admin, is_current=True)
    monkeypatch.setattr(users_router, "create_authorized_user", lambda *_args: None)
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_super_admin] = lambda: admin
    base = {"username": "scope_test", "password": "safe-password-2026"}
    try:
        with TestClient(app) as client:
            duplicate = client.post("/api/v1/authorized-users", json={**base, "coverage_scopes": [_province_payload(), _province_payload()]})
            mixed = client.post("/api/v1/authorized-users", json={**base, "coverage_scopes": [
                {"scope_level": "全国", "scope_name": "全国"},
                _province_payload(),
            ]})
    finally:
        app.dependency_overrides.clear()
    assert duplicate.status_code == 422
    assert mixed.status_code == 422


def test_super_admin_can_update_another_user(monkeypatch) -> None:
    """修改路由把启用状态和多个范围完整交给服务层。"""

    admin = _user(1, "admin_syt", UserRole.admin, is_current=True)
    updated = _user(2, "employee_test", UserRole.employee)
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        users_router,
        "update_authorized_user",
        lambda _db, user_id, **values: captured.update(user_id=user_id, **values) or updated,
    )
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_super_admin] = lambda: admin
    try:
        with TestClient(app) as client:
            response = client.patch(f"/api/v1/authorized-users/{UUID(int=2)}", json={
                "is_active": False,
                "salesperson_id": str(UUID(int=501)),
                "coverage_scopes": [_province_payload("吉林"), _province_payload("辽宁")],
            })
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert captured["is_active"] is False
    assert captured["salesperson_id"] == UUID(int=501)
    assert len(captured["coverage_scopes"]) == 2


def test_scope_update_flushes_removed_rows_before_reinserting_retained_scope(monkeypatch) -> None:
    """关联账号修改范围时把完整新范围交给销售与账号共享同步服务。"""

    target = SimpleNamespace(
        id=UUID(int=2), role=UserRole.employee, is_active=True,
        coverage_scopes=[SimpleNamespace(scope_level=SalesCoverageLevel.city, scope_name="杭州市")],
    )
    db = MagicMock()
    captured: dict[str, object] = {}
    monkeypatch.setattr(authorized_user_service, "_get_authorized_user", lambda *_args, **_kwargs: target)
    monkeypatch.setattr(
        authorized_user_service,
        "replace_salesperson_and_linked_account_scopes",
        lambda _db, salesperson_id, values: captured.update(
            salesperson_id=salesperson_id,
            scopes=list(values),
        ),
    )
    scopes = [
        AuthorizedUserCoverageScopeInput.model_validate({
            "scope_level": "市", "scope_name": "杭州市", "province": "浙江", "city": "杭州市", "amap_adcode": "330100",
        }),
        AuthorizedUserCoverageScopeInput.model_validate({
            "scope_level": "市", "scope_name": "重庆市", "province": "重庆", "city": "重庆市", "amap_adcode": "500100",
        }),
    ]

    authorized_user_service.update_authorized_user(db, target.id, is_active=True, salesperson_id=UUID(int=501), coverage_scopes=scopes)

    assert captured["salesperson_id"] == UUID(int=501)
    assert [scope.scope_name for scope in captured["scopes"]] == ["杭州市", "重庆市"]
    assert call.commit() in db.method_calls


def test_locked_authorized_user_query_does_not_join_nullable_salesperson() -> None:
    """账号更新只锁定账号主表，避免 PostgreSQL 拒绝锁定可空销售外连接。"""

    target = _user(2, "employee_test", UserRole.employee)
    db = MagicMock()
    db.scalar.return_value = target

    result = authorized_user_service._get_authorized_user(db, target.id, for_update=True)

    statement = db.scalar.call_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert result is target
    assert "FOR UPDATE" in sql
    assert "JOIN salesperson" not in sql


def test_super_admin_can_delete_another_user(monkeypatch) -> None:
    """删除成功路径把目标和当前超级管理员 ID 交给服务层并返回 204。"""

    admin = _user(1, "admin_syt", UserRole.admin, is_current=True)
    captured: dict[str, UUID] = {}
    monkeypatch.setattr(users_router, "delete_authorized_user", lambda _db, user_id, current_id: captured.update(user_id=user_id, current_id=current_id))
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_super_admin] = lambda: admin
    try:
        with TestClient(app) as client:
            response = client.delete(f"/api/v1/authorized-users/{UUID(int=2)}")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 204
    assert response.content == b""
    assert captured == {"user_id": UUID(int=2), "current_id": UUID(int=1)}
