"""普通公办本科第 06 批离线测试：锁定豫鄂湘粤范围、证据、排除项和定位输入。"""

from app.cli.import_verified_ordinary_undergraduate_universities_batch_06 import (
    MOE_2026_UNIVERSITY_DIRECTORY,
    OFFICIAL_MAIN_CAMPUS_ADDRESSES,
    ORDINARY_UNDERGRADUATE_BATCH_06_EXCLUSION_REASONS,
    VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_06,
    build_candidates,
)


def test_ordinary_undergraduate_batch_06_has_unique_verified_scope() -> None:
    """第 06 批必须只覆盖豫鄂湘粤 55 所已核验学校且不重复。"""

    seeds = VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_06
    names = {seed.name for seed in seeds}
    province_counts = {
        province: sum(seed.province == province for seed in seeds)
        for province in {seed.province for seed in seeds}
    }
    assert len(names) == 55
    assert province_counts == {"河南省": 26, "湖北省": 11, "湖南省": 13, "广东省": 5}
    assert {"河南国医学院", "湖北工程学院", "长沙工业学院", "大湾区大学", "深圳理工大学"} <= names


def test_ordinary_undergraduate_batch_06_keeps_evidence_and_safe_address() -> None:
    """每条正式候选必须保留公开证据，并使用低并发主校区定位输入。"""

    candidates = build_candidates()
    assert len(candidates) == 55
    assert all(candidate.website.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_url.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_excerpt and candidate.inclusion_reason for candidate in candidates)
    assert all(
        candidate.address == OFFICIAL_MAIN_CAMPUS_ADDRESSES.get(candidate.name, f"{candidate.city}{candidate.name}")
        for candidate in candidates
    )
    assert OFFICIAL_MAIN_CAMPUS_ADDRESSES["大湾区大学"].endswith("大学路16号")
    assert all("普通本科第06批" in candidate.tags for candidate in candidates)
    assert MOE_2026_UNIVERSITY_DIRECTORY.startswith("https://www.moe.gov.cn/")


def test_ordinary_undergraduate_batch_06_records_complete_public_boundary() -> None:
    """55 所纳入与 42 所排除必须完整对齐本轮 97 所教育部底表边界。"""

    excluded = ORDINARY_UNDERGRADUATE_BATCH_06_EXCLUSION_REASONS
    assert len(excluded) == 42
    assert len(VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_06) + len(excluded) == 97
    assert {
        "河南应用工程学院",
        "河南能源化工学院",
        "中南财经政法大学",
        "湖南第一师范学院",
        "香港科技大学（广州）",
        "深圳职业技术大学",
    } <= set(excluded)
    assert all(excluded.values())
