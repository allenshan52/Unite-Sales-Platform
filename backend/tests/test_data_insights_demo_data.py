"""全国数据洞察演示迁移的离线测试，锁定覆盖范围、季度样本与虚构标记。"""

import importlib.util
from collections import Counter
from pathlib import Path
from types import ModuleType


def _load_migration() -> ModuleType:
    """按路径加载数据洞察迁移，避免测试连接或修改真实数据库。"""

    migration_path = Path(__file__).parents[1] / "alembic" / "versions" / "20260825_0023_data_insights_demo_data.py"
    spec = importlib.util.spec_from_file_location("data_insights_demo_data", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_data_insights_demo_data_has_nationwide_quarter_depth() -> None:
    """新增数据必须补齐十三省，并使三年各已发生季度具备稳定样本。"""

    migration = _load_migration()
    migration._validate_demo_data()
    project_rows = migration._build_project_rows()
    quarter_counts = Counter(
        (row["signed_at"].year, (row["signed_at"].month - 1) // 3 + 1)
        for row in project_rows
    )

    assert len(migration.CUSTOMERS) == 26
    assert len({row[3] for row in migration.CUSTOMERS}) == 13
    assert len(project_rows) == 91
    assert len(migration._build_opportunity_rows()) == 52
    assert min(quarter_counts.values()) >= 7
    assert sum(row["opportunity_id"] is not None for row in project_rows) == 26
    assert all(row[1].startswith("优纳特演示成交单位") for row in migration.CUSTOMERS)
