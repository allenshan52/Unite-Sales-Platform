"""普通公办本科第 05 批离线测试：锁定皖闽赣鲁范围、证据、排除项和定位输入。"""

from app.cli.import_verified_ordinary_undergraduate_universities_batch_05 import (
    MOE_2026_UNIVERSITY_DIRECTORY,
    OFFICIAL_MAIN_CAMPUS_ADDRESSES,
    ORDINARY_UNDERGRADUATE_BATCH_05_EXCLUSION_REASONS,
    VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_05,
    build_candidates,
)


def test_ordinary_undergraduate_batch_05_has_unique_verified_scope() -> None:
    """第 05 批必须只覆盖皖闽赣鲁 61 所已核验学校且不重复。"""

    names = {seed.name for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_05}
    province_counts = {
        province: sum(seed.province == province for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_05)
        for province in {seed.province for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_05}
    }
    assert len(names) == 61
    assert province_counts == {"安徽省": 21, "福建省": 9, "江西省": 12, "山东省": 19}
    assert {"合肥理工学院", "龙岩学院", "抚州医药学院", "康复大学"} <= names


def test_ordinary_undergraduate_batch_05_keeps_evidence_and_safe_address() -> None:
    """每条正式候选必须保留公开证据，并以城市校名交给严格主校区 POI 策略。"""

    candidates = build_candidates()
    assert len(candidates) == 61
    assert all(candidate.website.startswith(("https://", "http://")) for candidate in candidates)
    assert all(candidate.evidence_url.startswith(("https://", "http://")) for candidate in candidates)
    assert all(candidate.evidence_excerpt for candidate in candidates)
    assert {seed.name for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_05 if seed.website == seed.evidence_url} == {
        "淮南师范学院",
        "南昌师范学院",
    }
    assert all(
        candidate.address == OFFICIAL_MAIN_CAMPUS_ADDRESSES.get(candidate.name, f"{candidate.city}{candidate.name}")
        for candidate in candidates
    )
    assert OFFICIAL_MAIN_CAMPUS_ADDRESSES == {"鲁东大学": "山东省烟台市芝罘区红旗中路186号"}
    assert all("普通公办本科" in candidate.tags for candidate in candidates)
    assert all("普通本科第05批" in candidate.tags for candidate in candidates)
    assert MOE_2026_UNIVERSITY_DIRECTORY.startswith("https://www.moe.gov.cn/")


def test_ordinary_undergraduate_batch_05_records_all_public_boundary_reasons() -> None:
    """本轮 27 所职业本科及非目标行业边界必须逐校保留原因。"""

    assert len(ORDINARY_UNDERGRADUATE_BATCH_05_EXCLUSION_REASONS) == 27
    assert {
        "安徽职业技术大学",
        "安徽财经大学",
        "黎明职业大学",
        "福建江夏学院",
        "江西财经大学",
        "豫章师范学院",
        "山东女子学院",
        "山东工商学院",
    } <= set(ORDINARY_UNDERGRADUATE_BATCH_05_EXCLUSION_REASONS)
    assert all(ORDINARY_UNDERGRADUATE_BATCH_05_EXCLUSION_REASONS.values())
