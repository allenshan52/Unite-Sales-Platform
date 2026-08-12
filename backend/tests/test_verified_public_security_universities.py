"""公安/公共安全本科专批离线测试：锁定全量范围、专科边界、官方证据及主校区输入。"""

from collections import Counter

from app.cli.import_verified_public_security_universities import (
    DEFERRED_PUBLIC_SECURITY_COLLEGES,
    MOE_2026_UNIVERSITY_DIRECTORY,
    OFFICIAL_MAIN_CAMPUS_ADDRESSES,
    VERIFIED_PUBLIC_SECURITY_UNIVERSITIES,
    build_candidates,
)
from app.models import EvidenceKind


def test_public_security_batch_has_expected_unique_undergraduate_scope() -> None:
    """专批必须完整覆盖 33 所本科，同时不把 23 所专科警校混入正式候选。"""

    names = {seed.name for seed in VERIFIED_PUBLIC_SECURITY_UNIVERSITIES}
    assert len(names) == 33
    assert len(DEFERRED_PUBLIC_SECURITY_COLLEGES) == 23
    assert names.isdisjoint(DEFERRED_PUBLIC_SECURITY_COLLEGES)
    assert {
        "中国人民公安大学", "中国刑事警察学院", "中央司法警官学院", "中国消防救援学院",
        "天津警察学院", "安徽公安学院", "内蒙古警察学院", "海南警察学院",
    } <= names
    assert Counter(seed.category for seed in VERIFIED_PUBLIC_SECURITY_UNIVERSITIES) == {
        "公安警察": 30,
        "司法警官": 1,
        "消防救援": 1,
        "刑事警察": 1,
    }


def test_public_security_candidates_keep_official_directory_evidence() -> None:
    """所有候选均应携带教育部官方目录证据、业务理由和公安专批标签。"""

    candidates = build_candidates()
    assert MOE_2026_UNIVERSITY_DIRECTORY.startswith("https://www.moe.gov.cn/")
    assert all(candidate.evidence_kind == EvidenceKind.official_directory for candidate in candidates)
    assert all(candidate.evidence_url == MOE_2026_UNIVERSITY_DIRECTORY for candidate in candidates)
    assert all("全量纳入" in candidate.inclusion_reason for candidate in candidates)
    assert all("公安高校全量批" in candidate.tags for candidate in candidates)


def test_public_security_candidates_use_safe_main_campus_queries() -> None:
    """地理编码必须使用公开主校区地址或城市加校名，禁止只用模糊校名生成 pin。"""

    candidates = build_candidates()
    assert all(
        candidate.address == OFFICIAL_MAIN_CAMPUS_ADDRESSES.get(candidate.name, f"{candidate.city}{candidate.name}")
        for candidate in candidates
    )
    assert OFFICIAL_MAIN_CAMPUS_ADDRESSES["海南警察学院"] == "海南省海口市秀英区定海大道1号"
    assert OFFICIAL_MAIN_CAMPUS_ADDRESSES["中国刑事警察学院"] == "辽宁省沈阳市皇姑区塔湾街83号"
    assert OFFICIAL_MAIN_CAMPUS_ADDRESSES["南京警察学院"] == "江苏省南京市栖霞区文澜路28号"
    assert OFFICIAL_MAIN_CAMPUS_ADDRESSES["郑州警察学院"] == "河南省郑州市金水区农业路31号"
