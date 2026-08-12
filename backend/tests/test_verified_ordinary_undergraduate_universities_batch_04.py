"""普通公办本科第 04 批离线测试：锁定沪苏浙范围、证据、排除项和定位输入。"""

from app.cli.import_verified_ordinary_undergraduate_universities_batch_04 import (
    MOE_2026_UNIVERSITY_DIRECTORY,
    ORDINARY_UNDERGRADUATE_BATCH_04_EXCLUSION_REASONS,
    VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_04,
    build_candidates,
)


def test_ordinary_undergraduate_batch_04_has_unique_verified_scope() -> None:
    """第 04 批必须只覆盖沪苏浙 43 所已核验学校且不重复。"""

    names = {seed.name for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_04}
    province_counts = {
        province: sum(seed.province == province for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_04)
        for province in {seed.province for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_04}
    }
    assert len(names) == 43
    assert province_counts == {"上海市": 7, "江苏省": 20, "浙江省": 16}
    assert {"上海海关学院", "连云港师范学院", "绍兴理工学院", "湖州师范大学"} <= names


def test_ordinary_undergraduate_batch_04_keeps_evidence_and_safe_address() -> None:
    """每条正式候选必须保留公开证据，并以城市校名交给严格主校区 POI 策略。"""

    candidates = build_candidates()
    assert len(candidates) == 43
    assert all(candidate.website.startswith(("https://", "http://")) for candidate in candidates)
    assert all(candidate.evidence_url.startswith(("https://", "http://")) for candidate in candidates)
    assert all(candidate.evidence_excerpt for candidate in candidates)
    assert all(candidate.address == f"{candidate.city}{candidate.name}" for candidate in candidates)
    assert all("普通公办本科" in candidate.tags for candidate in candidates)
    assert all("普通本科第04批" in candidate.tags for candidate in candidates)
    assert MOE_2026_UNIVERSITY_DIRECTORY.startswith("https://www.moe.gov.cn/")


def test_ordinary_undergraduate_batch_04_records_all_public_boundary_reasons() -> None:
    """本轮 18 所财经外语政法艺术及职业本科边界必须逐校保留原因。"""

    assert set(ORDINARY_UNDERGRADUATE_BATCH_04_EXCLUSION_REASONS) == {
        "上海外国语大学",
        "上海对外经贸大学",
        "上海戏剧学院",
        "上海政法学院",
        "上海立信会计金融学院",
        "上海财经大学",
        "上海音乐学院",
        "华东政法大学",
        "南京审计大学",
        "南京特殊教育师范学院",
        "南京艺术学院",
        "中国美术学院",
        "浙江传媒学院",
        "浙江外国语学院",
        "浙江财经大学",
        "浙江音乐学院",
        "温州理工学院",
        "浙江药科职业大学",
    }
    assert all(ORDINARY_UNDERGRADUATE_BATCH_04_EXCLUSION_REASONS.values())
