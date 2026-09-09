"""典型案例后端测试：覆盖公开脱敏、管理权限、输入校验和数据库约束声明。"""

from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError

from app.database import get_db
from app.main import app
from app.models import TypicalCase, UserRole
from app.sales_coverage import SalesCoverageLevel
from app.services.auth import get_current_admin
from app.services.typical_case_media import MAX_IMAGE_PIXELS, _normalize_image
from app.services.typical_cases import get_public_typical_case
from app.typical_case_schemas import TypicalCaseInput

CASE_ID = UUID("00000000-0000-4000-8000-000000006005")
PROJECT_ID = UUID("00000000-0000-4000-8000-000000005307")


def case_input_payload() -> dict[str, object]:
    """构造完全虚构且可发布的浙江演示案例输入。"""

    return {
        "sales_project_id": str(PROJECT_ID),
        "province": "浙江省",
        "province_adcode": "330000",
        "city": "金华市",
        "title": "研发中心分析平台一期",
        "subtitle": "虚构演示案例",
        "customer_display_name": "浙江某研发中心（演示）",
        "industry_label": "医药研发分析",
        "summary": "虚构案例摘要",
        "challenge": "虚构业务挑战",
        "solution": "虚构解决方案",
        "outcome": "虚构实施成果",
        "product_scope": "虚构产品与服务范围",
        "customer_quote": "虚构客户引语",
        "quote_attribution": "虚构项目负责人",
        "show_contract_amount": True,
        "is_published": True,
        "is_featured": True,
        "images": [{
            "path": "/cases/zhejiang-pharma.webp",
            "alt_text": "虚构的浙江研发分析平台",
            "caption": "演示图片",
            "is_cover": True,
        }],
        "metrics": [{"label": "验收阶段", "value": "3", "unit": "个"}],
    }


def admin_case_payload() -> dict[str, object]:
    """补充管理端只读字段，供路由成功合同测试使用。"""

    now = datetime(2026, 8, 18, 10, tzinfo=UTC).isoformat()
    return {
        **case_input_payload(),
        "id": str(CASE_ID),
        "project_name": "公司5研发中心分析平台",
        "organization_name": "公司5",
        "contract_amount": "760000.00",
        "signed_at": date(2025, 9, 27).isoformat(),
        "published_at": now,
        "created_at": now,
        "updated_at": now,
    }


def test_public_typical_case_map_returns_31_regions(monkeypatch, viewer_session: None) -> None:
    """公开地图一次返回完整大陆省级状态，不需要浏览器补业务统计。"""

    response_payload = {
        "total_regions": 31,
        "published_count": 1,
        "pending_count": 30,
        "regions": [{
            "province": "浙江省",
            "province_adcode": "330000",
            "status": "已上线",
            "case": {
                "id": str(CASE_ID), "province": "浙江省", "province_adcode": "330000", "city": "金华市",
                "title": "研发中心分析平台一期", "subtitle": "虚构演示案例",
                "customer_display_name": "浙江某研发中心（演示）", "industry_label": "医药研发分析",
                "summary": "虚构案例摘要", "cover_image": case_input_payload()["images"][0], "is_featured": True,
            },
        }],
    }
    monkeypatch.setattr("app.routers.typical_cases.list_public_typical_case_map", lambda _db: response_payload)
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/typical-cases")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["total_regions"] == 31
    assert response.json()["regions"][0]["case"]["customer_display_name"].endswith("（演示）")


def test_public_detail_hides_contract_amount_when_not_approved(viewer_session: None) -> None:
    """即使关联项目存在，未打开金额展示开关时公开 DTO 仍返回空金额。"""

    case = SimpleNamespace(
        id=CASE_ID, province="浙江省", province_adcode="330000", city="金华市",
        title="研发中心分析平台一期", subtitle=None, customer_display_name="浙江某研发中心（演示）",
        industry_label="医药研发分析", summary="虚构摘要", challenge="虚构挑战", solution="虚构方案",
        outcome="虚构成果", product_scope="虚构范围", customer_quote=None, quote_attribution=None,
        images=case_input_payload()["images"], metrics=case_input_payload()["metrics"], show_contract_amount=False,
        published_at=datetime(2026, 8, 18, tzinfo=UTC),
        sales_project=SimpleNamespace(name="虚构成交项目", signed_at=date(2025, 9, 27), contract_amount=Decimal("760000.00")),
    )

    class FakeDb:
        """只返回指定已发布案例，隔离公开裁剪逻辑。"""

        def scalar(self, _statement: object) -> object:
            """模拟单条 SQLAlchemy 查询。"""

            return case

    result = get_public_typical_case(FakeDb(), CASE_ID)  # type: ignore[arg-type]
    assert result.contract_amount is None
    assert not hasattr(result, "organization_name")
    assert not hasattr(result, "sales_project_id")


def test_typical_case_publish_validation_rejects_missing_cover() -> None:
    """发布状态必须具备图片和唯一封面，错误在写数据库前返回。"""

    payload = case_input_payload()
    payload["images"] = []
    try:
        TypicalCaseInput.model_validate(payload)
    except ValidationError as error:
        assert "封面图" in str(error)
    else:
        raise AssertionError("缺少封面的发布案例必须校验失败")


def test_admin_typical_case_requires_session() -> None:
    """案例管理列表不能被匿名读取。"""

    with TestClient(app) as client:
        response = client.get("/api/v1/admin-typical-cases")
    assert response.status_code == 401


def test_admin_typical_case_overview_returns_lightweight_rows(monkeypatch) -> None:
    """管理员列表固定返回 31 个省级槽位，且不夹带完整故事正文。"""

    payload = {
        "total_regions": 31,
        "configured_count": 1,
        "draft_count": 1,
        "published_count": 0,
        "items": [{
            "id": str(CASE_ID), "province": "浙江省", "province_adcode": "330000",
            "status": "草稿", "city": "金华市", "title": "研发中心分析平台一期",
            "customer_display_name": "浙江某研发中心（演示）", "industry_label": "医药研发分析",
            "cover_image": None, "is_featured": False,
            "updated_at": datetime(2026, 8, 18, 10, tzinfo=UTC).isoformat(),
        }],
    }
    monkeypatch.setattr(
        "app.routers.admin_typical_cases.list_admin_typical_case_overview",
        lambda _db, _scope: payload,
    )
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/admin-typical-cases")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["total_regions"] == 31
    assert "challenge" not in response.json()["items"][0]


def test_admin_typical_case_overview_receives_regional_scope(monkeypatch) -> None:
    """案例后台列表必须把区域账号范围传入服务层，公开案例全国策略不受影响。"""

    captured: dict[str, object] = {}

    def fake_overview(_db: object, scope: object) -> dict[str, object]:
        captured["scope"] = scope
        return {"total_regions": 0, "configured_count": 0, "draft_count": 0, "published_count": 0, "items": []}

    monkeypatch.setattr("app.routers.admin_typical_cases.list_admin_typical_case_overview", fake_overview)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(
        username="zhejiang_test",
        role=UserRole.employee,
        coverage_scopes=[SimpleNamespace(
            scope_level=SalesCoverageLevel.province,
            scope_name="浙江省",
            province="浙江省",
            city=None,
        )],
    )
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/admin-typical-cases")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert captured["scope"].visible_provinces == frozenset({"浙江"})


def test_admin_typical_case_image_upload_requires_session() -> None:
    """图片上传入口与案例编辑使用相同管理员会话保护。"""

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/admin-typical-cases/images",
            files={"file": ("cover.png", b"not-an-image", "image/png")},
        )
    assert response.status_code == 401


def test_admin_typical_case_image_upload_success(monkeypatch, tmp_path) -> None:
    """合法位图会被转为仓库可公开读取的 WebP 文件。"""

    buffer = BytesIO()
    Image.new("RGB", (80, 60), "#de5b35").save(buffer, format="PNG")
    settings = SimpleNamespace(
        typical_case_media_dir=tmp_path,
        typical_case_upload_max_bytes=8 * 1024 * 1024,
    )
    monkeypatch.setattr("app.services.typical_case_media.get_settings", lambda: settings)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/admin-typical-cases/images",
                files={"file": ("cover.png", buffer.getvalue(), "image/png")},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 201
    assert response.json()["path"].startswith("/cases/")
    assert response.json()["width"] == 80
    assert list(tmp_path.glob("*.webp"))


def test_admin_typical_case_image_upload_rejects_fake_image(monkeypatch, tmp_path) -> None:
    """伪造图片内容必须返回可读校验错误，不能落盘。"""

    settings = SimpleNamespace(
        typical_case_media_dir=tmp_path,
        typical_case_upload_max_bytes=8 * 1024 * 1024,
    )
    monkeypatch.setattr("app.services.typical_case_media.get_settings", lambda: settings)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/admin-typical-cases/images",
                files={"file": ("cover.png", b"not-an-image", "image/png")},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
    assert not list(tmp_path.iterdir())


def test_typical_case_image_rejects_pixel_bomb_before_decode(monkeypatch, tmp_path) -> None:
    """超限尺寸必须在 load 解码前返回 413，避免压缩炸弹消耗大量内存。"""

    loaded = False

    class OversizedImage:
        size = (MAX_IMAGE_PIXELS + 1, 1)

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def load(self) -> None:
            nonlocal loaded
            loaded = True

    monkeypatch.setattr("app.services.typical_case_media.Image.open", lambda *_args: OversizedImage())
    with pytest.raises(HTTPException) as error:
        _normalize_image(b"compressed-demo", tmp_path)
    assert error.value.status_code == 413
    assert loaded is False
    assert not list(tmp_path.iterdir())


def test_admin_typical_case_create_success(monkeypatch) -> None:
    """认证管理员可提交完整案例，路由传递经过校验的聚合输入。"""

    captured: dict[str, object] = {}

    def fake_create(_db: object, payload: TypicalCaseInput, username: str) -> dict[str, object]:
        """捕获省份、封面和管理员用户名。"""

        captured["values"] = (payload.province, payload.images[0].is_cover, username)
        return admin_case_payload()

    monkeypatch.setattr("app.routers.admin_typical_cases.create_typical_case", fake_create)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(username="admin_test")
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/admin-typical-cases", json=case_input_payload())
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 201
    assert response.json()["contract_amount"] == "760000.00"
    assert captured["values"] == ("浙江省", True, "admin_test")


def test_typical_case_model_declares_publication_constraints() -> None:
    """ORM 元数据必须与迁移保持同省、同项目和推荐位唯一约束。"""

    index_names = {index.name for index in TypicalCase.__table__.indexes}
    constraint_names = {constraint.name for constraint in TypicalCase.__table__.constraints}
    assert {
        "uq_typical_case_province",
        "uq_typical_case_project",
        "uq_typical_case_featured",
    } <= index_names
    assert "ck_typical_case_featured_published" in constraint_names
