"""普通公办本科第 01 批离线测试：锁定河北、山西范围、证据、排除项和定位输入。"""

from app.cli.import_verified_ordinary_undergraduate_universities_batch_01 import (
    MOE_2026_UNIVERSITY_DIRECTORY,
    OFFICIAL_MAIN_CAMPUS_ADDRESSES,
    ORDINARY_UNDERGRADUATE_BATCH_01_EXCLUSION_REASONS,
    VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_01,
    build_candidates,
)


def test_ordinary_undergraduate_batch_01_has_unique_verified_scope() -> None:
    """第 01 批必须仅覆盖河北、山西 46 所已核验学校且不重复。"""

    names = {seed.name for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_01}
    province_counts = {
        province: sum(seed.province == province for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_01)
        for province in {seed.province for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_01}
    }
    assert len(names) == 46
    assert province_counts == {"河北省": 27, "山西省": 19}
    assert {"河北环境工程学院", "应急管理大学", "山西医药学院", "长治学院"} <= names


def test_ordinary_undergraduate_batch_01_keeps_evidence_and_safe_address() -> None:
    """每条正式候选都要保留公开证据，并以城市和校名交给严格 POI 策略。"""

    candidates = build_candidates()
    assert len(candidates) == 46
    assert all(candidate.website.startswith(("https://", "http://")) for candidate in candidates)
    assert all(candidate.evidence_url.startswith(("https://", "http://")) for candidate in candidates)
    assert all(candidate.evidence_excerpt for candidate in candidates)
    assert all(
        candidate.address == OFFICIAL_MAIN_CAMPUS_ADDRESSES.get(candidate.name, f"{candidate.city}{candidate.name}")
        for candidate in candidates
    )
    assert OFFICIAL_MAIN_CAMPUS_ADDRESSES["应急管理大学"].endswith("学院大街467号")
    assert all("普通公办本科" in candidate.tags for candidate in candidates)
    assert MOE_2026_UNIVERSITY_DIRECTORY.startswith("https://www.moe.gov.cn/")


def test_ordinary_undergraduate_batch_01_records_out_of_scope_reasons() -> None:
    """纯财经和传媒边界必须有逐校原因，避免后续把它们误认为尚未筛选。"""

    assert set(ORDINARY_UNDERGRADUATE_BATCH_01_EXCLUSION_REASONS) == {
        "河北金融学院", "河北经贸大学", "山西传媒学院", "山西财经大学"
    }
    assert all(ORDINARY_UNDERGRADUATE_BATCH_01_EXCLUSION_REASONS.values())
