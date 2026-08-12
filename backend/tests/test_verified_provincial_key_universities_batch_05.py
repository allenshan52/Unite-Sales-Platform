"""省属重点本科第 05 批离线测试：锁定桂琼渝川范围、排除项、证据和主校区查询。"""

from collections import Counter

from app.cli.import_verified_provincial_key_universities_batch_05 import (
    VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_05,
    build_candidates,
)


def test_provincial_key_batch_05_has_unique_four_region_scope() -> None:
    """第 05 批应恰好包含四地 37 所目标公办本科，且校名不重复。"""

    names = {seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_05}
    province_counts = Counter(
        seed.province for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_05
    )
    assert len(names) == 37
    assert province_counts == {
        "广西壮族自治区": 13,
        "海南省": 3,
        "重庆市": 8,
        "四川省": 13,
    }
    assert {
        "桂林医科大学",
        "海南热带海洋学院",
        "重庆科技大学",
        "四川轻化工大学",
        "中国民用航空飞行学院",
    } <= names


def test_provincial_key_batch_05_excludes_existing_and_out_of_scope_schools() -> None:
    """既有、纯文财经艺术和民办院校不得混入本批正式候选。"""

    names = {seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_05}
    assert {
        "广西大学",
        "海南大学",
        "重庆大学",
        "西南大学",
        "四川大学",
        "四川农业大学",
        "成都中医药大学",
        "广西艺术学院",
        "广西财经学院",
        "西南政法大学",
        "四川美术学院",
        "重庆工商大学",
        "西南财经大学",
        "四川音乐学院",
        "成都外国语学院",
        "四川工业科技学院",
    }.isdisjoint(names)


def test_provincial_key_batch_05_keeps_evidence_and_safe_address() -> None:
    """每所候选必须保存官方证据，并以城市与校名进行严格主校区 POI 检索。"""

    candidates = build_candidates()
    assert len(candidates) == 37
    assert all(candidate.website.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_url.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_title for candidate in candidates)
    assert all(candidate.evidence_excerpt for candidate in candidates)
    assert all(candidate.address == f"{candidate.city}{candidate.name}" for candidate in candidates)
    assert all("省属重点本科" in candidate.tags for candidate in candidates)
    assert all("官网专业证据" in candidate.tags for candidate in candidates)
    assert all("省属重点第05批" in candidate.tags for candidate in candidates)
