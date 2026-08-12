"""省属重点本科第 02 批离线测试：锁定华东范围、官网证据与安全主校区检索输入。"""

from app.cli.import_verified_provincial_key_universities_batch_02 import (
    VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_02,
    build_candidates,
)


def test_provincial_key_batch_02_has_unique_east_china_scope() -> None:
    """第 02 批必须恰好覆盖上海、江苏、浙江的 24 所已核验公办本科。"""

    names = {seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_02}
    provinces = {seed.province for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_02}
    assert len(names) == 24
    assert provinces == {"上海市", "江苏省", "浙江省"}
    assert {
        "上海理工大学",
        "江苏大学",
        "南京工业大学",
        "浙江工业大学",
        "中国计量大学",
        "浙江海洋大学",
    } <= names


def test_provincial_key_batch_02_keeps_official_evidence_and_safe_address() -> None:
    """候选须保存高校官方证据，并仅以城市和校名交给严格主校区 POI 匹配。"""

    candidates = build_candidates()
    assert len(candidates) == 24
    assert all(candidate.website.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_url.startswith("https://") for candidate in candidates)
    assert all(
        "edu.cn" in candidate.evidence_url or ".net" in candidate.evidence_url
        for candidate in candidates
    )
    assert all(candidate.address == f"{candidate.city}{candidate.name}" for candidate in candidates)
    assert all("省属重点本科" in candidate.tags for candidate in candidates)
    assert all("官网专业证据" in candidate.tags for candidate in candidates)
