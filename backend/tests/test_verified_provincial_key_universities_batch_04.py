"""省属重点本科第 04 批离线测试：锁定豫鄂湘粤范围、排除项、证据和主校区查询。"""

from collections import Counter

from app.cli.import_verified_provincial_key_universities_batch_04 import (
    VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_04,
    build_candidates,
)


def test_provincial_key_batch_04_has_unique_four_province_scope() -> None:
    """第 04 批应恰好包含四省 49 所目标公办本科，且校名不重复。"""

    names = {seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_04}
    province_counts = Counter(
        seed.province for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_04
    )
    assert len(names) == 49
    assert province_counts == {
        "河南省": 7,
        "湖北省": 13,
        "湖南省": 9,
        "广东省": 20,
    }
    assert {
        "河南农业大学",
        "湖北中医药大学",
        "湖南农业大学",
        "湖南理工大学",
        "广东海洋大学",
        "佛山大学",
    } <= names


def test_provincial_key_batch_04_excludes_out_of_scope_schools() -> None:
    """军队、纯文财经艺术、中外合作和非独立分校区不得混入省属目标名单。"""

    names = {seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_04}
    assert {
        "海军工程大学",
        "中南财经政法大学",
        "湖北美术学院",
        "武汉音乐学院",
        "湖南工商大学",
        "广东外语外贸大学",
        "广东以色列理工学院",
        "香港中文大学（深圳）",
        "哈尔滨工业大学（深圳）",
        "湖南理工学院",
    }.isdisjoint(names)


def test_provincial_key_batch_04_keeps_evidence_and_safe_address() -> None:
    """每所候选必须保存官方证据，并以城市与校名进行严格主校区 POI 检索。"""

    candidates = build_candidates()
    assert len(candidates) == 49
    assert all(candidate.website.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_url.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_title for candidate in candidates)
    assert all(candidate.evidence_excerpt for candidate in candidates)
    assert all(candidate.address == f"{candidate.city}{candidate.name}" for candidate in candidates)
    assert all("省属重点本科" in candidate.tags for candidate in candidates)
    assert all("官网专业证据" in candidate.tags for candidate in candidates)
    assert all("省属重点第04批" in candidate.tags for candidate in candidates)
