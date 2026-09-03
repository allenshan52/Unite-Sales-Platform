"""单位完整性离线测试：锁定并发唯一约束与安全中文冲突响应。"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models import Organization, OrganizationSite
from app.services.organizations import _raise_organization_conflict


class CommitConflictSession:
    """记录冲突路径是否执行回滚，不连接真实数据库。"""

    def __init__(self) -> None:
        self.rolled_back = False

    def rollback(self) -> None:
        """模拟 SQLAlchemy 会话回滚。"""

        self.rolled_back = True


def test_organization_models_lock_name_and_primary_site_uniqueness() -> None:
    """模型元数据必须保留标准化名称和单一主地点唯一索引。"""

    organization_indexes = {index.name: index for index in Organization.__table__.indexes}
    site_indexes = {index.name: index for index in OrganizationSite.__table__.indexes}
    assert organization_indexes["uq_organization_normalized_name"].unique is True
    assert site_indexes["uq_organization_site_primary"].unique is True
    assert str(site_indexes["uq_organization_site_primary"].dialect_options["postgresql"]["where"]) == "is_primary"


@pytest.mark.parametrize(
    ("constraint_name", "expected_detail"),
    [
        ("uq_organization_normalized_name", "已存在同名单位"),
        ("organization_unified_social_credit_code_key", "统一社会信用代码"),
        ("uq_organization_site_primary", "一个主地点"),
        ("unknown_constraint", "数据与现有记录冲突"),
    ],
)
def test_integrity_conflicts_rollback_and_return_safe_chinese_409(constraint_name: str, expected_detail: str) -> None:
    """唯一约束冲突必须回滚，并避免把数据库异常直接暴露给管理员。"""

    session = CommitConflictSession()
    original = SimpleNamespace(diag=SimpleNamespace(constraint_name=constraint_name))
    error = IntegrityError("INSERT INTO organization ...", {}, original)

    with pytest.raises(HTTPException) as raised:
        _raise_organization_conflict(session, error)  # type: ignore[arg-type]

    assert session.rolled_back is True
    assert raised.value.status_code == 409
    assert expected_detail in raised.value.detail
    assert "INSERT" not in raised.value.detail
