"""新增“双一流”高校清单测试：锁定 25 所纳入、6 所排除及每校官网证据。"""

from app.cli.import_verified_double_first_class_universities import (
    EXCLUDED_NEW_DOUBLE_FIRST_CLASS_UNIVERSITIES,
    MOE_DOUBLE_FIRST_CLASS_DIRECTORY,
    VERIFIED_DOUBLE_FIRST_CLASS_UNIVERSITIES,
    build_candidates,
)


def test_double_first_class_difference_has_complete_screening_conclusion() -> None:
    """确保 31 所新增建设高校均有纳入或排除结论，避免差集静默漏校。"""

    included = {seed.name for seed in VERIFIED_DOUBLE_FIRST_CLASS_UNIVERSITIES}
    excluded = {seed.name for seed in EXCLUDED_NEW_DOUBLE_FIRST_CLASS_UNIVERSITIES}
    assert len(included) == 25
    assert len(excluded) == 6
    assert not included.intersection(excluded)
    assert "中国人民公安大学" in included
    assert "中国美术学院" in excluded


def test_double_first_class_candidates_keep_official_evidence_and_safe_address_input() -> None:
    """每所正式候选必须保存高校官网证据，并以城市加校名交给严格 POI 主校区匹配。"""

    candidates = build_candidates()
    assert len(candidates) == 25
    assert all(candidate.website.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_url.startswith("https://") for candidate in candidates)
    assert all("edu.cn" in candidate.evidence_url or ".ac.cn" in candidate.evidence_url for candidate in candidates)
    assert all(candidate.address == f"{candidate.city}{candidate.name}" for candidate in candidates)
    assert MOE_DOUBLE_FIRST_CLASS_DIRECTORY.startswith("https://www.moe.gov.cn/")
