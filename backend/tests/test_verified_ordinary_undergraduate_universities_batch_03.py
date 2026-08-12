"""普通公办本科第 03 批离线测试：锁定吉林、黑龙江范围、证据、排除项和定位输入。"""

from app.cli.import_verified_ordinary_undergraduate_universities_batch_03 import (
    MOE_2026_UNIVERSITY_DIRECTORY,
    ORDINARY_UNDERGRADUATE_BATCH_03_EXCLUSION_REASONS,
    VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_03,
    build_candidates,
)


def test_ordinary_undergraduate_batch_03_has_unique_verified_scope() -> None:
    """第 03 批必须仅覆盖吉林、黑龙江 28 所已核验学校且不重复。"""

    names = {seed.name for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_03}
    province_counts = {
        province: sum(seed.province == province for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_03)
        for province in {seed.province for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_03}
    }
    assert len(names) == 28
    assert province_counts == {"吉林省": 13, "黑龙江省": 15}
    assert {"吉林工商学院", "吉林农业科技学院", "哈尔滨商业大学", "黑龙江工业学院"} <= names


def test_ordinary_undergraduate_batch_03_keeps_evidence_and_safe_address() -> None:
    """每条正式候选必须保留公开证据，并以城市校名交给严格主校区 POI 策略。"""

    candidates = build_candidates()
    assert len(candidates) == 28
    assert all(candidate.website.startswith(("https://", "http://")) for candidate in candidates)
    assert all(candidate.evidence_url.startswith(("https://", "http://")) for candidate in candidates)
    assert all(candidate.evidence_excerpt for candidate in candidates)
    assert all(candidate.address == f"{candidate.city}{candidate.name}" for candidate in candidates)
    assert all("普通公办本科" in candidate.tags for candidate in candidates)
    assert all("普通本科第03批" in candidate.tags for candidate in candidates)
    assert MOE_2026_UNIVERSITY_DIRECTORY.startswith("https://www.moe.gov.cn/")


def test_ordinary_undergraduate_batch_03_records_out_of_scope_reasons() -> None:
    """财经、艺术和职业本科边界必须有逐校原因，避免后续重复筛选。"""

    assert set(ORDINARY_UNDERGRADUATE_BATCH_03_EXCLUSION_REASONS) == {
        "吉林财经大学",
        "吉林艺术学院",
        "吉林铁道职业技术大学",
        "长春汽车职业技术大学",
        "长春职业技术大学",
        "哈尔滨金融学院",
        "哈尔滨音乐学院",
        "哈尔滨建筑科技职业大学",
        "哈尔滨职业技术大学",
        "黑龙江农业工程职业技术大学",
    }
    assert all(ORDINARY_UNDERGRADUATE_BATCH_03_EXCLUSION_REASONS.values())
