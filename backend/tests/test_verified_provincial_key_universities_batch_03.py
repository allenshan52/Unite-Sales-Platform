"""省属重点本科第 03 批离线测试：锁定皖闽赣鲁范围、证据、去重和主校区查询。"""

from collections import Counter

from app.cli.import_verified_provincial_key_universities_batch_03 import (
    VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_03,
    build_candidates,
)


def test_provincial_key_batch_03_has_unique_four_province_scope() -> None:
    """第 03 批应恰好包含四省 44 所已筛选公办本科，且校名不重复。"""

    names = {seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_03}
    province_counts = Counter(
        seed.province for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_03
    )
    assert len(names) == 44
    assert province_counts == {
        "安徽省": 7,
        "福建省": 11,
        "江西省": 12,
        "山东省": 14,
    }
    assert {
        "安徽农业大学",
        "福建农林大学",
        "江西理工大学",
        "山东第一医科大学",
    } <= names
    assert "安徽建筑大学" not in names
    assert "江西财经大学" not in names
    assert "山东财经大学" not in names


def test_provincial_key_batch_03_keeps_evidence_and_safe_address() -> None:
    """每所候选必须保留官方证据，并用城市与校名进行严格主校区 POI 检索。"""

    candidates = build_candidates()
    assert len(candidates) == 44
    assert all(candidate.website.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_url.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_title for candidate in candidates)
    assert all(candidate.evidence_excerpt for candidate in candidates)
    assert all(candidate.address == f"{candidate.city}{candidate.name}" for candidate in candidates)
    assert all("省属重点本科" in candidate.tags for candidate in candidates)
    assert all("官网专业证据" in candidate.tags for candidate in candidates)
    assert all("省属重点第03批" in candidate.tags for candidate in candidates)
