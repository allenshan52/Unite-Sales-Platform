"""985/211 已核验导入清单测试：保证名单规模、名称映射和主校区编码输入可重复验证。"""

from app.cli.import_verified_985_211_universities import (
    MOE_211_DIRECTORY,
    MOE_985_DIRECTORY,
    VERIFIED_985_UNIVERSITIES,
    VERIFIED_ONLY_211_UNIVERSITIES,
    build_candidates,
)


def test_verified_985_and_only_211_lists_have_the_promised_scope() -> None:
    """防止后续编辑误删或混入被筛除的财经、语言和艺术类学校。"""

    assert len(VERIFIED_985_UNIVERSITIES) == 39
    assert len(VERIFIED_ONLY_211_UNIVERSITIES) == 60
    assert len({seed.name for seed in VERIFIED_985_UNIVERSITIES + VERIFIED_ONLY_211_UNIVERSITIES}) == 99
    assert "北京外国语大学" not in {seed.name for seed in VERIFIED_ONLY_211_UNIVERSITIES}
    assert "西南财经大学" not in {seed.name for seed in VERIFIED_ONLY_211_UNIVERSITIES}


def test_candidates_use_official_entries_and_name_only_address_for_safe_poi_resolution() -> None:
    """每条记录保留官网入口，地址仅作为高德严格同名主校区 POI 的检索起点。"""

    candidates = build_candidates()
    assert len(candidates) == 99
    assert all(candidate.website.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_url == candidate.website for candidate in candidates)
    assert all(candidate.address == f"{candidate.city}{candidate.name}" for candidate in candidates)
    assert MOE_211_DIRECTORY.startswith("https://www.moe.gov.cn/")
    assert MOE_985_DIRECTORY.startswith("https://www.moe.gov.cn/")
