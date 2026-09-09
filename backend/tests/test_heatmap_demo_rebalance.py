"""成交热力演示重排迁移的离线测试，锁定范围、沿海目标和安全标记。"""

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_migration() -> ModuleType:
    """按路径加载重排迁移，不连接或修改实际数据库。"""

    migration_path = Path(__file__).parents[1] / "alembic" / "versions" / "20260826_0025_rebalance_heatmap_demo_data.py"
    spec = importlib.util.spec_from_file_location("heatmap_demo_rebalance", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_heatmap_demo_rebalance_moves_only_eight_marked_customers_to_coast() -> None:
    """重排必须一对一落到八个沿海城市，并保留可逆的原始地点快照。"""

    migration = _load_migration()
    migration._validate_rebalance()
    rows = migration.REBALANCED_SITES

    assert len(rows) == 8
    assert all(row["organization_id"].startswith("00000000-0000-4000-8000-0000000230") for row in rows)
    assert all(row["source"] != row["target"] for row in rows)
    assert len({row["target"][1] for row in rows}) == 8
    source = Path(migration.__file__).read_text(encoding="utf-8")
    assert "data_insights_demo" in source
    assert "result.rowcount != 1" in source
