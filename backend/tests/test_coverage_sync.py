"""覆盖范围同步服务测试：锁定销售到多个关联账号的完整扇出行为。"""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

from app.models import AdminUserCoverageScope
from app.sales_coverage import SalesCoverageLevel
from app.services import coverage_sync


def test_salesperson_scopes_replace_all_linked_account_scopes(monkeypatch) -> None:
    """同一销售关联两个账号时，两者均获得销售当前范围的独立副本。"""

    salesperson_id = UUID(int=501)
    user_ids = [UUID(int=601), UUID(int=602)]
    scope = SimpleNamespace(
        scope_level=SalesCoverageLevel.province,
        scope_name="河北",
        province="河北",
        city=None,
        amap_adcode=None,
    )
    db = MagicMock()
    db.scalars.side_effect = [SimpleNamespace(all=lambda: [scope]), SimpleNamespace(all=lambda: user_ids)]
    monkeypatch.setattr(coverage_sync, "_lock_salesperson", lambda *_args: None)

    count = coverage_sync.sync_linked_account_scopes(db, salesperson_id)

    assert count == 2
    added = db.add_all.call_args.args[0]
    assert len(added) == 2
    assert all(isinstance(item, AdminUserCoverageScope) for item in added)
    assert {item.user_id for item in added} == set(user_ids)
    assert {item.scope_name for item in added} == {"河北"}
    assert db.flush.call_count == 3
