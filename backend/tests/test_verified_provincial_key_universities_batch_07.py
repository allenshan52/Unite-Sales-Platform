"""省属重点本科第 07 批离线测试：锁定贵云藏范围、筛选原因、官方证据与主校区查询。"""

from collections import Counter

from app.cli.import_verified_provincial_key_universities_batch_07 import (
    PROVINCIAL_KEY_BATCH_07_EXCLUSION_REASONS,
    VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_07,
    build_candidates,
)


def test_provincial_key_batch_07_has_expected_unique_scope() -> None:
    """第 07 批应恰好覆盖贵 7、云 8、藏 2 所证据完整的目标公办本科，且校名唯一。"""

    names = {seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_07}
    assert len(names) == 17
    assert Counter(seed.province for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_07) == {
        "贵州省": 7,
        "云南省": 8,
        "西藏自治区": 2,
    }
    assert {"贵州师范大学", "昆明理工大学", "西藏农牧大学", "西藏藏医药大学"} <= names
    assert {"贵州大学", "云南大学", "西藏大学", "西藏民族大学"}.isdisjoint(names)


def test_provincial_key_batch_07_records_boundary_reasons() -> None:
    """既有、财经艺术、公安、职业、民办、证据不足及跨省校址必须分别说明，不能混称无专业。"""

    reasons = PROVINCIAL_KEY_BATCH_07_EXCLUSION_REASONS
    assert all("不重复" in reasons[name] for name in {"贵州大学", "云南大学", "西藏大学"})
    assert "财经类" in reasons["贵州财经大学"]
    assert "艺术类" in reasons["云南艺术学院"]
    assert "公安专批" in reasons["贵州警察学院"]
    assert "职业本科" in reasons["昆明冶金职业大学"]
    assert "普通本科补充批" in reasons["遵义师范学院"]
    assert "民办本科" in reasons["昆明医科大学海源学院"]
    assert "陕西咸阳" in reasons["西藏民族大学"]


def test_provincial_key_batch_07_keeps_evidence_and_safe_address() -> None:
    """每所候选必须留存官方证据，并以城市加校名进行严格主校区 POI 检索。"""

    candidates = build_candidates()
    assert len(candidates) == 17
    assert all(candidate.website.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_url.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_title and candidate.evidence_excerpt for candidate in candidates)
    assert all(candidate.address == f"{candidate.city}{candidate.name}" for candidate in candidates)
    assert all("省属重点本科" in candidate.tags for candidate in candidates)
    assert all("官网专业证据" in candidate.tags for candidate in candidates)
    assert all("省属重点第07批" in candidate.tags for candidate in candidates)
