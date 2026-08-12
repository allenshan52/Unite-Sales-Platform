"""高校官网取证首批的离线校验：保证每条候选均有可追溯证据与可编码的完整校址。"""

from app.cli.import_verified_universities_batch_01 import MOE_HIGHER_EDUCATION_DIRECTORY, VERIFIED_UNIVERSITIES


def test_verified_university_batch_has_official_evidence_and_address() -> None:
    """首批逐校候选必须同时具备官网证据、四级地址信息和用于审核筛选的标签。"""

    assert len(VERIFIED_UNIVERSITIES) == 4
    for candidate in VERIFIED_UNIVERSITIES:
        assert candidate.evidence_url.startswith("https://")
        assert ".edu.cn" in candidate.evidence_url
        assert all((candidate.province, candidate.city, candidate.district, candidate.address))
        assert "官网专业证据" in candidate.tags


def test_verified_batch_uses_the_same_official_page_as_the_directory_base() -> None:
    """取证批次须以底表实际发布页回写原始行，不能误用教育部栏目索引页。"""

    assert MOE_HIGHER_EDUCATION_DIRECTORY.endswith("t20260618_1441074.html")
