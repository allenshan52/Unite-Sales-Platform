"""省属重点本科第 09 批离线测试：锁定京津范围、筛选原因、证据与主校区查询。"""

from collections import Counter

from app.cli.import_verified_provincial_key_universities_batch_09 import (
    MOE_2026_UNIVERSITY_DIRECTORY,
    OFFICIAL_MAIN_CAMPUS_ADDRESSES,
    PROVINCIAL_KEY_BATCH_09_EXCLUSION_REASONS,
    VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_09,
    build_candidates,
)


def test_provincial_key_batch_09_has_expected_unique_scope() -> None:
    """第 09 批应覆盖北京 12、天津 8 所证据完整且尚未入库的目标公办本科。"""

    names = {seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_09}
    assert len(names) == 20
    assert Counter(seed.province for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_09) == {
        "北京市": 12,
        "天津市": 8,
    }
    assert {
        "中国矿业大学（北京）", "中国石油大学（北京）", "中国地质大学（北京）", "首都医科大学",
        "中国民航大学", "天津科技大学", "天津职业技术师范大学", "天津城建大学",
    } <= names
    assert {"北京大学", "北京工业大学", "南开大学", "天津工业大学"}.isdisjoint(names)


def test_provincial_key_batch_09_records_boundary_reasons() -> None:
    """既有、行业不符、公安、证据不足、职业和民办项必须保留准确原因。"""

    reasons = PROVINCIAL_KEY_BATCH_09_EXCLUSION_REASONS
    assert all("不重复" in reasons[name] for name in {"北京大学", "北京工业大学", "南开大学", "天津工业大学"})
    assert "财经" in reasons["中央财经大学"]
    assert "公安" in reasons["北京警察学院"]
    assert "普通本科补充批" in reasons["北京信息科技大学"]
    assert "职业教育" in reasons["天津职业大学"]
    assert "民办本科" in reasons["天津天狮学院"]


def test_provincial_key_batch_09_keeps_traceable_evidence_and_safe_address() -> None:
    """每所候选必须保留公开证据、教育部底表来源和城市加校名的严格 POI 查询。"""

    candidates = build_candidates()
    assert len(candidates) == 20
    assert MOE_2026_UNIVERSITY_DIRECTORY.startswith("https://www.moe.gov.cn/")
    assert all(candidate.website.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_url.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_title and candidate.evidence_excerpt for candidate in candidates)
    assert all(
        candidate.address == OFFICIAL_MAIN_CAMPUS_ADDRESSES.get(candidate.name, f"{candidate.city}{candidate.name}")
        for candidate in candidates
    )
    assert OFFICIAL_MAIN_CAMPUS_ADDRESSES["天津职业技术师范大学"] == "天津市河西区大沽南路1310号"
    assert all("省属重点第09批" in candidate.tags for candidate in candidates)
