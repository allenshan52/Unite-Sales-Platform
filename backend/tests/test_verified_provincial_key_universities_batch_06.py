"""省属重点本科第 06 批离线测试：锁定四川困难批、筛选原因、证据和主校区查询。"""

from app.cli.import_verified_provincial_key_universities_batch_06 import (
    PROVINCIAL_KEY_BATCH_06_EXCLUSION_REASONS,
    VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_06,
    build_candidates,
)


def test_provincial_key_batch_06_has_unique_sichuan_scope() -> None:
    """第 06 批应恰好包含四川 8 所证据完整的目标公办本科，且校名不重复。"""

    names = {seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_06}
    assert len(names) == 8
    assert {seed.province for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_06} == {"四川省"}
    assert names == {
        "西昌学院",
        "四川师范大学",
        "西华师范大学",
        "绵阳师范学院",
        "宜宾学院",
        "西南民族大学",
        "四川旅游学院",
        "四川民族学院",
    }


def test_provincial_key_batch_06_records_exclusion_reasons_by_boundary() -> None:
    """不纳入与暂缓项必须各有具体原因，不能笼统记作没有相关专业。"""

    reasons = PROVINCIAL_KEY_BATCH_06_EXCLUSION_REASONS
    assert "财经类" in reasons["西南财经大学"]
    assert "艺术类" in reasons["四川音乐学院"]
    assert "暂缓到普通本科" in reasons["阿坝师范学院"]
    assert "有材料与环境专业" in reasons["成都工业学院"]
    assert "公安专批" in reasons["四川警察学院"]
    assert all("职业本科" in reasons[name] for name in {
        "四川工程职业技术大学",
        "成都航空职业技术大学",
        "成都轻工职业技术大学",
        "四川建筑职业技术大学",
        "四川交通职业技术大学",
    })
    assert all("民办本科" in reasons[name] for name in {
        "成都东软学院",
        "成都艺术职业大学",
        "电子科技大学成都学院",
        "成都理工大学工程技术学院",
        "四川传媒学院",
        "成都银杏酒店管理学院",
        "成都文理学院",
        "四川工商学院",
        "成都外国语学院",
        "四川工业科技学院",
        "成都锦城学院",
        "西南财经大学天府学院",
        "四川大学锦江学院",
        "四川文化艺术学院",
        "绵阳城市学院",
        "西南交通大学希望学院",
        "四川电影电视学院",
        "吉利学院",
    })


def test_provincial_key_batch_06_keeps_evidence_and_safe_address() -> None:
    """每所候选必须保存官方证据，并以城市与校名进行严格主校区 POI 检索。"""

    candidates = build_candidates()
    assert len(candidates) == 8
    assert all(candidate.website.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_url.startswith("https://") for candidate in candidates)
    assert all(candidate.evidence_title for candidate in candidates)
    assert all(candidate.evidence_excerpt for candidate in candidates)
    assert all(candidate.address == f"{candidate.city}{candidate.name}" for candidate in candidates)
    assert all("省属重点本科" in candidate.tags for candidate in candidates)
    assert all("官网专业证据" in candidate.tags for candidate in candidates)
    assert all("省属重点第06批" in candidate.tags for candidate in candidates)
