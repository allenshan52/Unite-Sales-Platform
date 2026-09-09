"""优纳特热力图演示迁移的离线合同测试，锁定数据规模、口径和虚构标记。"""

import importlib.util
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from types import ModuleType


def _load_migration() -> ModuleType:
    """按文件路径加载数字开头的 Alembic 模块，避免连接真实数据库。"""

    migration_path = Path(__file__).parents[1] / "alembic" / "versions" / "20260825_0022_unite_heatmap_demo_data.py"
    spec = importlib.util.spec_from_file_location("unite_heatmap_demo_data", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unite_demo_data_supports_all_amount_levels() -> None:
    """新增数据必须形成计划中的成交/意向规模，并覆盖五档省级合同金额。"""

    migration = _load_migration()
    migration._validate_demo_data()
    province_by_customer = {row[0]: row[3] for row in migration.CUSTOMERS}
    province_totals: dict[str, Decimal] = defaultdict(Decimal)
    for _number, customer_number, _salesperson_number, _name, amount, _signed_at in migration.PROJECTS:
        province_totals[province_by_customer[customer_number]] += Decimal(amount)

    assert len(migration.CUSTOMERS) == 12
    assert len(migration.PROJECTS) == 18
    assert len(migration.OPPORTUNITIES) == 14
    assert len(province_totals) == 12
    assert min(province_totals.values()) == Decimal("120000.00")
    assert max(province_totals.values()) == Decimal("4200000.00")
    assert all(row[1].startswith("优纳特演示成交单位") for row in migration.CUSTOMERS)
