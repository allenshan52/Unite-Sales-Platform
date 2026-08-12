"""普通公办本科第 02 批离线测试：锁定内蒙古、辽宁范围、证据、排除项和定位输入。"""

from app.cli.import_verified_ordinary_undergraduate_universities_batch_02 import (
    MOE_2026_UNIVERSITY_DIRECTORY,
    OFFICIAL_MAIN_CAMPUS_ADDRESSES,
    ORDINARY_UNDERGRADUATE_BATCH_02_EXCLUSION_REASONS,
    VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_02,
    build_candidates,
)


def test_ordinary_undergraduate_batch_02_has_unique_verified_scope() -> None:
    """第 02 批必须仅覆盖内蒙古、辽宁 36 所已核验学校且不重复。"""

    names = {seed.name for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_02}
    province_counts = {
        province: sum(seed.province == province for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_02)
        for province in {seed.province for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_02}
    }
    assert len(names) == 36
    assert province_counts == {"内蒙古自治区": 11, "辽宁省": 25}
    assert {"赤峰大学", "朝阳师范学院", "中国医科大学", "营口理工学院"} <= names


def test_ordinary_undergraduate_batch_02_keeps_evidence_and_safe_address() -> None:
    """每条正式候选都要保留公开证据，并以城市校名或法定地址交给严格 POI 策略。"""

    candidates = build_candidates()
    assert len(candidates) == 36
    assert all(candidate.website.startswith(("https://", "http://")) for candidate in candidates)
    assert all(candidate.evidence_url.startswith(("https://", "http://")) for candidate in candidates)
    assert all(candidate.evidence_excerpt for candidate in candidates)
    assert all(
        candidate.address == OFFICIAL_MAIN_CAMPUS_ADDRESSES.get(candidate.name, f"{candidate.city}{candidate.name}")
        for candidate in candidates
    )
    assert OFFICIAL_MAIN_CAMPUS_ADDRESSES["朝阳师范学院"].endswith("龙山街四段966号")
    assert all("普通公办本科" in candidate.tags for candidate in candidates)
    assert all("普通本科第02批" in candidate.tags for candidate in candidates)
    assert MOE_2026_UNIVERSITY_DIRECTORY.startswith("https://www.moe.gov.cn/")


def test_ordinary_undergraduate_batch_02_records_out_of_scope_reasons() -> None:
    """财经、外语、艺术和职业本科边界必须有逐校原因，避免后续重复筛选。"""

    assert set(ORDINARY_UNDERGRADUATE_BATCH_02_EXCLUSION_REASONS) == {
        "内蒙古财经大学",
        "内蒙古艺术学院",
        "内蒙古建筑职业技术大学",
        "兴安职业技术大学",
        "呼和浩特职业技术大学",
        "大连外国语大学",
        "东北财经大学",
        "沈阳音乐学院",
        "鲁迅美术学院",
    }
    assert all(ORDINARY_UNDERGRADUATE_BATCH_02_EXCLUSION_REASONS.values())
