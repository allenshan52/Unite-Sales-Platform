"""省属重点本科第 01 批离线测试：锁定范围、官方证据和安全的主校区检索输入。"""

from app.cli.import_verified_provincial_key_universities_batch_01 import (
    MOE_UNIVERSITY_DIRECTORY,
    VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_01,
    build_candidates,
)


def test_provincial_key_batch_01_has_unique_verified_scope() -> None:
    """首批每所学校只能出现一次，并覆盖计划中的华北、东北六个省级区域。"""

    names = {seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_01}
    provinces = {seed.province for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_01}
    assert len(names) == 23
    assert provinces == {"河北省", "山西省", "内蒙古自治区", "辽宁省", "吉林省", "黑龙江省"}
    assert {"河北大学", "沈阳药科大学", "吉林农业大学", "哈尔滨理工大学"} <= names


def test_provincial_key_batch_01_keeps_official_evidence_and_safe_address() -> None:
    """正式候选必须保存学校官网证据，并仅以城市和校名触发严格主校区 POI 匹配。"""

    candidates = build_candidates()
    assert len(candidates) == 23
    assert all(candidate.website.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_url.startswith("https://") for candidate in candidates)
    assert all("edu.cn" in candidate.evidence_url or ".net" in candidate.evidence_url for candidate in candidates)
    assert all(candidate.address == f"{candidate.city}{candidate.name}" for candidate in candidates)
    assert all("省属重点本科" in candidate.tags for candidate in candidates)
    assert MOE_UNIVERSITY_DIRECTORY.startswith("https://www.moe.gov.cn/")
