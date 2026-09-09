"""公司地点搜索 API 合同：覆盖登录保护、参数校验和高德候选返回。"""

from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.routers import location_search
from app.services.auth import get_current_admin


def test_logged_in_user_can_search_company_locations(monkeypatch) -> None:
    """有效后台会话可按关键词获得不含服务端 Key 的地点候选。"""

    monkeypatch.setattr(location_search, "search_amap_places", lambda keyword: [{
        "name": keyword, "address": "上海市浦东新区演示大道18号", "province": "上海市",
        "city": "上海市", "district": "浦东新区", "amap_adcode": "310115",
        "longitude": "121.506377", "latitude": "31.245105",
    }])
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="location_test")
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/admin-location-search", params={"keyword": "演示公司"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["name"] == "演示公司"
    assert "key" not in response.text.lower()


def test_location_search_rejects_short_keyword() -> None:
    """不足两个字符的关键词在调用外部服务前由 FastAPI 拒绝。"""

    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="location_test")
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/admin-location-search", params={"keyword": "沪"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_location_search_requires_login() -> None:
    """无有效后台会话时不能借搜索接口调用高德配额。"""

    def reject_request() -> None:
        """模拟认证依赖拒绝未登录请求。"""

        raise HTTPException(status_code=401, detail="请先登录")

    app.dependency_overrides[get_current_admin] = reject_request
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/admin-location-search", params={"keyword": "演示公司"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
