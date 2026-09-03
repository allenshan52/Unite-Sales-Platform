"""后端测试夹具：显式提供普通员工会话，避免把受保护主站接口误称为匿名接口。"""

from types import SimpleNamespace

import pytest

from app.main import app
from app.models import UserRole
from app.sales_coverage import SalesCoverageLevel
from app.services.auth import get_current_user


@pytest.fixture
def viewer_session():
    """为只读主站合同测试注入普通员工身份，并在用例结束后清理覆盖。"""

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        username="employee_test",
        role=UserRole.employee,
        coverage_scopes=[SimpleNamespace(scope_level=SalesCoverageLevel.national, scope_name="全国", province=None, city=None)],
    )
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_user, None)
