"""省属重点本科第 08 批离线测试：锁定西北五省区范围、筛选原因、证据与主校区查询。"""

from collections import Counter

from app.cli.import_verified_provincial_key_universities_batch_08 import (
    MOE_2026_UNIVERSITY_DIRECTORY,
    PROVINCIAL_KEY_BATCH_08_EXCLUSION_REASONS,
    VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_08,
    build_candidates,
)


def test_provincial_key_batch_08_has_expected_unique_scope() -> None:
    """第 08 批应覆盖陕 12、甘 7、青 2、宁 1、新 5 所证据完整的目标公办本科。"""

    names = {seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_08}
    assert len(names) == 27
    assert Counter(seed.province for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_08) == {
        "陕西省": 12,
        "甘肃省": 7,
        "青海省": 2,
        "宁夏回族自治区": 1,
        "新疆维吾尔自治区": 5,
    }
    assert {"西藏民族大学", "甘肃农业大学", "青海理工学院", "宁夏医科大学", "昌吉学院"} <= names
    assert {"西北大学", "青海大学", "宁夏大学", "新疆大学", "石河子大学"}.isdisjoint(names)


def test_provincial_key_batch_08_records_boundary_reasons() -> None:
    """既有、专类、职业、民办和证据不足项必须各有准确原因，不能统称没有专业。"""

    reasons = PROVINCIAL_KEY_BATCH_08_EXCLUSION_REASONS
    assert all("不重复" in reasons[name] for name in {"西北大学", "青海大学", "宁夏大学", "新疆大学", "石河子大学"})
    assert "财经类" in reasons["兰州财经大学"]
    assert "公安专批" in reasons["新疆警察学院"]
    assert "普通本科补充批" in reasons["喀什大学"]
    assert "职业本科" in reasons["新疆农业职业技术大学"]
    assert "民办本科" in reasons["西安建筑科技大学华清学院"]


def test_provincial_key_batch_08_keeps_traceable_evidence_and_safe_address() -> None:
    """每所候选必须有官方证据、当前教育部底表来源和城市加校名的严格 POI 查询。"""

    candidates = build_candidates()
    assert len(candidates) == 27
    assert MOE_2026_UNIVERSITY_DIRECTORY.startswith("https://www.moe.gov.cn/")
    assert all(candidate.website.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_url.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_title and candidate.evidence_excerpt for candidate in candidates)
    assert all(candidate.address == f"{candidate.city}{candidate.name}" for candidate in candidates)
    assert all("省属重点第08批" in candidate.tags for candidate in candidates)
